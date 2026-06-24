"""Phase 7 API: gamification profile, leaderboard, XP, and mini-games."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents import game_master
from app.api.deps import get_current_user
from app.database import get_db
from app.gamification import service
from app.models.rag import Document, DocChunk
from app.models.user import User

router = APIRouter(prefix="/game", tags=["game"])


@router.get("/profile")
def profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return service.profile_json(db, service.get_profile(db, user.id))


@router.get("/leaderboard")
def leaderboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return service.leaderboard(db)


class XpIn(BaseModel):
    amount: int = service.XP_MINIGAME_WIN
    reason: str = "mini-game"


@router.post("/xp")
def add_xp(payload: XpIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Cap per-call XP so mini-games can't be abused to farm levels.
    amount = max(0, min(payload.amount, 50))
    return service.award_xp(db, user.id, amount, payload.reason)


@router.get("/sources")
def sources(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """The learner's uploaded materials that arcade games can be built from."""
    docs = (db.query(Document).filter(Document.user_id == user.id)
            .order_by(Document.created_at.desc()).all())
    return [{"id": d.id, "title": d.title, "kind": d.kind} for d in docs]


class TopicIn(BaseModel):
    topic: str = ""
    document_id: str | None = None  # build the game from the learner's own material


def _context_for(db: Session, user: User, payload: "TopicIn") -> tuple[str, str]:
    """Return (topic, context). If a document is chosen, pull its text as context
    and use its title as the topic when none was typed."""
    if not payload.document_id:
        return payload.topic or "general knowledge", ""
    doc = db.get(Document, payload.document_id)
    if doc is None or doc.user_id != user.id:
        return payload.topic or "general knowledge", ""
    text = "\n".join(c.content for c in
                     db.query(DocChunk).filter(DocChunk.document_id == doc.id)
                     .order_by(DocChunk.ordinal).all())
    return (payload.topic or doc.title), text


@router.post("/flashcards")
def flashcards(payload: TopicIn, user: User = Depends(get_current_user),
               db: Session = Depends(get_db)):
    topic, context = _context_for(db, user, payload)
    return {"cards": game_master.flashcards(topic, context=context)}


@router.post("/boss")
def boss(payload: TopicIn, user: User = Depends(get_current_user),
         db: Session = Depends(get_db)):
    topic, context = _context_for(db, user, payload)
    return {"questions": game_master.boss_quiz(topic, context=context)}
