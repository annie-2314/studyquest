"""Phase 3 API: multimodal image solving + a basic RAG knowledge base."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents import rag_agent
from app.agents.vision import solve_image
from app.api.deps import get_current_user
from app.database import get_db
from app.models.rag import Document
from app.models.user import User
from app.rag import store

router = APIRouter(prefix="/study", tags=["study"])

_MAX_IMAGE_BYTES = 8 * 1024 * 1024  # 8 MB


@router.post("/solve-image")
async def solve_image_route(
    file: UploadFile = File(...),
    question: str = Form(""),
    user: User = Depends(get_current_user),
):
    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(status_code=400, detail="Please upload an image file")
    data = await file.read()
    if len(data) > _MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image too large (max 8 MB)")
    answer = solve_image(data, file.content_type or "image/png", question)
    return {"answer": answer}


class DocIn(BaseModel):
    title: str
    text: str


@router.post("/documents", status_code=201)
def add_document(payload: DocIn, user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="Document text is empty")
    doc = store.add_document(db, user.id, payload.title or "Untitled", payload.text)
    return {"id": doc.id, "title": doc.title, "chunks": len(doc.chunks)}


@router.get("/documents")
def list_documents(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    docs = (db.query(Document).filter(Document.user_id == user.id)
            .order_by(Document.created_at.desc()).all())
    return [{"id": d.id, "title": d.title, "kind": d.kind, "chunks": len(d.chunks)} for d in docs]


class AskIn(BaseModel):
    query: str
    document_id: str | None = None


@router.post("/ask")
def ask(payload: AskIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not payload.query.strip():
        raise HTTPException(status_code=400, detail="Question is empty")
    return rag_agent.answer(db, user.id, payload.query, payload.document_id)
