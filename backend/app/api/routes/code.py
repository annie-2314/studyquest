"""Phase 5 API: run code in the sandbox and get an AI code review."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.agents.code_review import review_code
from app.api.deps import get_current_user
from app.models.user import User
from app.sandbox import run_code

router = APIRouter(prefix="/code", tags=["code"])


class RunIn(BaseModel):
    language: str = "python"
    code: str
    stdin: str = ""


@router.post("/run")
def run(payload: RunIn, user: User = Depends(get_current_user)):
    return run_code(payload.language, payload.code, payload.stdin)


class ReviewIn(BaseModel):
    language: str = "python"
    code: str
    task: str = ""
    stdin: str = ""


@router.post("/review")
def review(payload: ReviewIn, user: User = Depends(get_current_user)):
    result = run_code(payload.language, payload.code, payload.stdin)
    review_out = review_code(payload.language, payload.code, result, payload.task)
    return {"run": result, **review_out}
