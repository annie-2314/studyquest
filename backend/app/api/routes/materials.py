"""Grounded-RAG materials API: ingest PDFs / pasted text, list them, and ask
questions answered ONLY from the student's own sources with citations.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents import grounded
from app.api.deps import get_current_user
from app.database import get_db
from app.materials import figures, ingest, store
from app.models.material import Material
from app.models.user import User
from app.transcribe import TranscribeError, transcribe_youtube

router = APIRouter(prefix="/materials", tags=["materials"])

_MAX_PDF_BYTES = 20 * 1024 * 1024  # 20 MB


def _material_json(m: Material) -> dict:
    return {"id": m.id, "title": m.title, "kind": m.kind, "chunks": len(m.chunks),
            "created_at": m.created_at.isoformat()}


class TextIn(BaseModel):
    title: str
    text: str


@router.post("/ingest/text", status_code=201)
def ingest_text(payload: TextIn, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    chunks = ingest.chunk_text(payload.text)
    if not chunks:
        raise HTTPException(status_code=400, detail="No text to ingest.")
    mat = store.add_material(db, user.id, payload.title or "Pasted notes", chunks, kind="text")
    return _material_json(mat)


@router.post("/ingest", status_code=201)
async def ingest_file(file: UploadFile = File(...), title: str = Form(""),
                      user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Ingest a PDF (other types: send text to /materials/ingest/text)."""
    data = await file.read()
    if len(data) > _MAX_PDF_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 20 MB)")
    name = (file.filename or "").lower()
    if not (name.endswith(".pdf") or (file.content_type or "").endswith("pdf")):
        raise HTTPException(status_code=400, detail="Please upload a PDF, or use the paste-text option.")
    try:
        chunks = ingest.chunk_pdf(data)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not read that PDF: {e}")
    # Multimodal: index extracted figures (captioned if ENABLE_IMAGE_CAPTIONS is on).
    chunks = chunks + figures.figure_chunks(data)
    if not chunks:
        raise HTTPException(status_code=422, detail="No extractable text found in that PDF.")
    mat = store.add_material(db, user.id, title or file.filename or "PDF", chunks, kind="pdf")
    return _material_json(mat)


class UrlIn(BaseModel):
    url: str
    title: str = ""


@router.post("/ingest/url", status_code=201)
def ingest_url(payload: UrlIn, user: User = Depends(get_current_user),
               db: Session = Depends(get_db)):
    """Ingest a YouTube/audio URL → transcript → grounded-RAG index (reuses the
    transcription pipeline)."""
    try:
        segments = transcribe_youtube(payload.url)
    except TranscribeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    text = " ".join(s.get("text", "") for s in segments)
    chunks = ingest.chunk_text(text)
    if not chunks:
        raise HTTPException(status_code=422, detail="No transcript text found for that URL.")
    mat = store.add_material(db, user.id, payload.title or "Video transcript", chunks, kind="video")
    return _material_json(mat)


@router.get("")
def list_materials(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    mats = (db.query(Material).filter(Material.user_id == user.id)
            .order_by(Material.created_at.desc()).all())
    return [_material_json(m) for m in mats]


class AskIn(BaseModel):
    question: str
    material_id: str | None = None  # None = search across all the user's materials


@router.post("/ask")
def ask(payload: AskIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="Question is empty")
    return grounded.answer(db, user.id, payload.question, material_id=payload.material_id)
