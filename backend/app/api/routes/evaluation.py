"""Phase 10 API: observability status + evaluation harness endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.eval import harness
from app.models.user import User
from app.observability import init_tracing

router = APIRouter(prefix="/eval", tags=["eval"])


@router.get("/obs-status")
def obs_status(user: User = Depends(get_current_user)):
    # Re-reads current config; reflects whether LangSmith tracing is active.
    return init_tracing()


class JudgeIn(BaseModel):
    question: str
    answer: str


@router.post("/explanation")
def judge(payload: JudgeIn, user: User = Depends(get_current_user)):
    return harness.judge_explanation(payload.question, payload.answer)


@router.get("/quiz-improvement")
def quiz_improvement(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return harness.quiz_improvement(db, user.id)
