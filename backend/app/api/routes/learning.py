"""Knowledge-tracing API: per-concept mastery, a spaced-review queue, and a
manual attempt-recording hook (used by quizzes and for testing).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.learning import service
from app.models.user import User

router = APIRouter(prefix="/learning", tags=["learning"])


@router.get("/mastery")
def mastery(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Per-concept mastery (0..1) plus a time-series for the over-time chart."""
    return service.mastery_overview(db, user.id)


@router.get("/review-queue")
def review_queue(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Concepts due for review (or weakest-first) to drive adaptive practice."""
    return service.review_queue(db, user.id)


class AttemptIn(BaseModel):
    concept: str
    correct: bool


@router.post("/attempt")
def record_attempt(payload: AttemptIn, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    """Record a graded attempt against a concept (updates BKT mastery)."""
    row = service.record_attempt(db, user.id, payload.concept, payload.correct)
    return {"concept": row.concept, "p_known": round(row.p_known, 3)} if row else {}
