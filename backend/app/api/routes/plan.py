"""Phase 8 API: generate a personalized study plan (the crew) and export a PDF."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.memory import load_memory
from app.api.deps import get_current_user
from app.crew.study_plan import run_study_plan_crew
from app.database import get_db
from app.models.user import User
from app.pdf import build_study_guide_pdf

router = APIRouter(prefix="/plan", tags=["plan"])


class PlanIn(BaseModel):
    topic: str


@router.post("")
def make_plan(payload: PlanIn, user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    # Personalize using the learner's stored weak spots (Phase 2 memory).
    mem = load_memory(db, user.id)
    return run_study_plan_crew(payload.topic, weak_spots=list(mem.weak_spots or []))


class PdfIn(BaseModel):
    # The frontend posts back the plan it received from /plan.
    topic: str
    personalized_for: list[str] = []
    modules: list[dict] = []
    review_notes: str = ""


@router.post("/pdf")
def plan_pdf(payload: PdfIn, user: User = Depends(get_current_user)):
    data = build_study_guide_pdf(payload.model_dump())
    filename = f"studyquest-{payload.topic[:30].replace(' ', '_')}.pdf"
    return Response(content=data, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})
