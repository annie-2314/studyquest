"""Phase 8 API: generate a personalized learning ROADMAP (the crew) + PDF export.

Given a goal, weekly time, target timeline and preferred language, a role crew
(Planner -> Resource-Curator -> Reviewer) builds a time-boxed roadmap with
resource links — exportable as a PDF.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.memory import load_memory
from app.api.deps import get_current_user
from app.crew.roadmap import run_roadmap_crew
from app.database import get_db
from app.models.user import User
from app.pdf import build_roadmap_pdf

router = APIRouter(prefix="/plan", tags=["plan"])


class PlanIn(BaseModel):
    goal: str
    hours_per_week: int = 5
    timeline: str = "8 weeks"
    language: str = ""


@router.post("")
def make_plan(payload: PlanIn, user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    # Personalize using the learner's stored weak spots (Phase 2 memory).
    mem = load_memory(db, user.id)
    return run_roadmap_crew(
        payload.goal,
        hours_per_week=payload.hours_per_week,
        timeline=payload.timeline,
        language=payload.language,
        weak_spots=list(mem.weak_spots or []),
    )


class PdfIn(BaseModel):
    # The frontend posts back the roadmap it received from /plan.
    goal: str = ""
    hours_per_week: int = 0
    timeline: str = ""
    language: str = ""
    personalized_for: list[str] = []
    phases: list[dict] = []
    review_notes: str = ""


@router.post("/pdf")
def plan_pdf(payload: PdfIn, user: User = Depends(get_current_user)):
    data = build_roadmap_pdf(payload.model_dump())
    filename = f"roadmap-{payload.goal[:30].replace(' ', '_') or 'plan'}.pdf"
    return Response(content=data, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})
