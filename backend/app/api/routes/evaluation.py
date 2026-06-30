"""Phase 10 API: observability status + evaluation harness endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.config import settings
from app.database import get_db
from app.eval import harness
from app.models.evaluation import EvalResult
from app.models.user import User
from app.observability import init_tracing

router = APIRouter(prefix="/eval", tags=["eval"])


def _save_eval(db: Session, user_id: str, kind: str, score: float, passed: bool, detail: str):
    row = EvalResult(user_id=user_id, kind=kind, score=float(score),
                     passed=bool(passed), detail=detail[:1000])
    db.add(row)
    db.commit()


@router.get("/obs-status")
def obs_status(user: User = Depends(get_current_user)):
    # Re-reads current config; reflects whether LangSmith tracing is active.
    return init_tracing()


@router.get("/traces")
def traces(user: User = Depends(get_current_user)):
    """Recent LangSmith runs for the configured project, surfaced in-app so the
    traces are viewable without leaving StudyQuest. Returns an empty list (never
    errors) when tracing is off or the LangSmith API can't be reached."""
    if not (settings.langchain_api_key and settings.langchain_tracing_v2):
        return {"enabled": False, "runs": []}
    try:
        from langsmith import Client

        client = Client(api_key=settings.langchain_api_key)
        # is_root=True → one entry per request (top-level trace), not every nested step.
        raw = list(client.list_runs(project_name=settings.langchain_project,
                                    is_root=True, limit=15))
    except Exception:
        return {"enabled": True, "runs": [], "error": "Could not reach LangSmith."}

    runs = []
    for r in raw:
        latency_ms = None
        if getattr(r, "start_time", None) and getattr(r, "end_time", None):
            latency_ms = round((r.end_time - r.start_time).total_seconds() * 1000)
        runs.append({
            "name": getattr(r, "name", "run"),
            "run_type": getattr(r, "run_type", ""),
            "status": "error" if getattr(r, "error", None) else "ok",
            "latency_ms": latency_ms,
            "tokens": getattr(r, "total_tokens", None),
            "start_time": r.start_time.isoformat() if getattr(r, "start_time", None) else None,
        })
    return {"enabled": True, "runs": runs}


class JudgeIn(BaseModel):
    question: str
    answer: str


@router.post("/explanation")
def judge(payload: JudgeIn, user: User = Depends(get_current_user)):
    return harness.judge_explanation(payload.question, payload.answer)


@router.get("/quiz-improvement")
def quiz_improvement(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return harness.quiz_improvement(db, user.id)


class FactualityIn(BaseModel):
    answer: str
    sources: list[str] = []


@router.post("/factuality")
def factuality(payload: FactualityIn, user: User = Depends(get_current_user),
               db: Session = Depends(get_db)):
    """LLM-as-judge: is the answer grounded in the provided sources, or hallucinated?"""
    v = harness.judge_factuality(payload.answer, payload.sources)
    _save_eval(db, user.id, "factuality", v["score"], v["grounded"], v["rationale"])
    return v


class QuizValidityIn(BaseModel):
    question: str
    options: list[str]
    answer_index: int = 0


@router.post("/quiz-validity")
def quiz_validity(payload: QuizValidityIn, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    v = harness.judge_quiz_validity(payload.question, payload.options, payload.answer_index)
    _save_eval(db, user.id, "quiz_validity", v["score"], v["valid"], v["rationale"])
    return v


@router.get("/results")
def results(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Recent persisted eval results for the report widget."""
    rows = (db.query(EvalResult).filter(EvalResult.user_id == user.id)
            .order_by(EvalResult.created_at.desc()).limit(20).all())
    return [{"kind": r.kind, "score": round(r.score, 2), "passed": r.passed,
             "detail": r.detail, "at": r.created_at.isoformat() if r.created_at else None}
            for r in rows]
