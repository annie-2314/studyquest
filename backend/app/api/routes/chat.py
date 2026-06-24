"""Chat tutor API: REST for conversations/history + a WebSocket for live,
streaming, supervised tutor responses."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from jose import JWTError
from sqlalchemy.orm import Session

from app.agents import memory as mem_mod
from app.agents import supervisor
from app.agents.specialists import specialist_name
from app.api.deps import get_current_user
from app.core.security import decode_token
from app.database import SessionLocal, get_db
from app.models.learning import Conversation, Message
from app.models.user import User

router = APIRouter(prefix="/chat", tags=["chat"])


# ---------- REST: conversations & history ----------

@router.get("/conversations")
def list_conversations(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    convs = (db.query(Conversation).filter(Conversation.user_id == user.id)
             .order_by(Conversation.created_at.desc()).all())
    return [{"id": c.id, "title": c.title, "created_at": c.created_at.isoformat()} for c in convs]


@router.post("/conversations", status_code=201)
def create_conversation(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv = Conversation(user_id=user.id, title="New chat")
    db.add(conv); db.commit(); db.refresh(conv)
    return {"id": conv.id, "title": conv.title, "created_at": conv.created_at.isoformat()}


@router.get("/conversations/{conversation_id}/messages")
def get_messages(conversation_id: str, user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    conv = db.get(Conversation, conversation_id)
    if conv is None or conv.user_id != user.id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return [{"role": m.role, "agent": m.agent, "content": m.content,
             "created_at": m.created_at.isoformat()} for m in conv.messages]


# ---------- WebSocket: live streaming tutor ----------

def _user_from_token(token: str, db: Session) -> User | None:
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            return None
        return db.get(User, payload["sub"])
    except (JWTError, KeyError):
        return None


@router.websocket("/ws")
async def chat_ws(websocket: WebSocket):
    """Protocol:
    client -> {"token","conversation_id"?,"message"}
    server -> {"type":"route","agent":..} then {"type":"token","data":..}* then
              {"type":"done","conversation_id":..}
    """
    await websocket.accept()
    db = SessionLocal()
    try:
        while True:
            payload = await websocket.receive_json()
            user = _user_from_token(payload.get("token", ""), db)
            if user is None:
                await websocket.send_json({"type": "error", "detail": "Unauthorized"})
                await websocket.close()
                return

            user_message = (payload.get("message") or "").strip()
            if not user_message:
                await websocket.send_json({"type": "error", "detail": "Empty message"})
                continue

            # Resolve / create conversation (verifying ownership).
            conv_id = payload.get("conversation_id")
            conv = db.get(Conversation, conv_id) if conv_id else None
            if conv is None or conv.user_id != user.id:
                conv = Conversation(user_id=user.id, title=user_message[:40])
                db.add(conv); db.commit(); db.refresh(conv)

            history = [{"role": m.role, "content": m.content} for m in conv.messages]
            mem = mem_mod.load_memory(db, user.id)
            memory_ctx = mem_mod.memory_context(mem)

            # Persist the user's message.
            db.add(Message(conversation_id=conv.id, role="user", content=user_message))
            db.commit()

            # Stream the supervised answer.
            answer_parts: list[str] = []
            route = supervisor.DEFAULT_ROUTE
            async for kind, value in supervisor.stream_turn(user.id, history, user_message, memory_ctx):
                if kind == "route":
                    route = value
                    await websocket.send_json({"type": "route", "agent": specialist_name(route)})
                else:
                    answer_parts.append(value)
                    await websocket.send_json({"type": "token", "data": value})

            answer = "".join(answer_parts)
            db.add(Message(conversation_id=conv.id, role="assistant", agent=route, content=answer))
            db.commit()

            # Update durable student memory from this turn.
            mem_mod.update_summary(db, user.id, user_message)

            await websocket.send_json({"type": "done", "conversation_id": conv.id})
    except WebSocketDisconnect:
        pass
    finally:
        db.close()
