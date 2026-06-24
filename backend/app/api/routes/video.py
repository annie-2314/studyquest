"""Phase 6 API: Video RAG. Ingest a video (YouTube URL or uploaded file),
transcribe it, index timestamped chunks, then answer questions with [mm:ss]
citations. Reuses the Phase-3 RAG store/agent."""
from __future__ import annotations

import os
import tempfile

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents import rag_agent
from app.api.deps import get_current_user
from app.database import get_db
from app.models.rag import Document
from app.models.user import User
from app.rag import store
from app.transcribe import TranscribeError, transcribe_file, transcribe_youtube

router = APIRouter(prefix="/video", tags=["video"])

_MAX_UPLOAD = 100 * 1024 * 1024  # 100 MB


def _video_json(d: Document) -> dict:
    return {"id": d.id, "title": d.title, "kind": d.kind, "chunks": len(d.chunks)}


class YtIn(BaseModel):
    url: str
    title: str = ""


@router.post("/from-youtube", status_code=201)
def from_youtube(payload: YtIn, user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    try:
        segments = transcribe_youtube(payload.url)
    except TranscribeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    doc = store.add_segments_document(db, user.id, payload.title or "YouTube video", segments)
    return _video_json(doc)


@router.post("/upload", status_code=201)
async def upload_video(file: UploadFile = File(...), user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    data = await file.read()
    if len(data) > _MAX_UPLOAD:
        raise HTTPException(status_code=413, detail="File too large (max 100 MB)")
    suffix = os.path.splitext(file.filename or "")[1] or ".mp4"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        tmp.write(data)
        tmp.close()
        try:
            segments = transcribe_file(tmp.name)
        except TranscribeError as e:
            # 501: capability not installed; clear guidance, not a crash.
            raise HTTPException(status_code=501, detail=str(e))
    finally:
        os.unlink(tmp.name)
    doc = store.add_segments_document(db, user.id, file.filename or "Uploaded video", segments)
    return _video_json(doc)


@router.get("")
def list_videos(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    docs = (db.query(Document).filter(Document.user_id == user.id, Document.kind == "video")
            .order_by(Document.created_at.desc()).all())
    return [_video_json(d) for d in docs]


class AskIn(BaseModel):
    question: str


@router.post("/{doc_id}/ask")
def ask_video(doc_id: str, payload: AskIn, user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    doc = db.get(Document, doc_id)
    if doc is None or doc.user_id != user.id:
        raise HTTPException(status_code=404, detail="Video not found")
    return rag_agent.answer(db, user.id, payload.question, document_id=doc_id)
