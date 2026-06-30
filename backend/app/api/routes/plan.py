"""Phase 8 API: generate a personalized learning ROADMAP (the crew) + PDF export.

Given a goal, weekly time, target timeline and preferred language, a role crew
(Planner -> Resource-Curator -> Reviewer) builds a time-boxed roadmap with
resource links — exportable as a PDF.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.memory import load_memory
from app.api.deps import get_current_user
from app.crew.roadmap import run_roadmap_crew
from app.database import get_db
from app.models.roadmap import Roadmap
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
    roadmap = run_roadmap_crew(
        payload.goal,
        hours_per_week=payload.hours_per_week,
        timeline=payload.timeline,
        language=payload.language,
        weak_spots=list(mem.weak_spots or []),
    )
    # Persist it so the learner can revisit it later.
    row = Roadmap(user_id=user.id, goal=roadmap["goal"],
                  hours_per_week=roadmap["hours_per_week"], timeline=roadmap["timeline"],
                  language=roadmap["language"], data=json.dumps(roadmap))
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, **roadmap}


@router.get("/list")
def list_roadmaps(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Past roadmaps the learner has built, newest first."""
    rows = (db.query(Roadmap).filter(Roadmap.user_id == user.id)
            .order_by(Roadmap.created_at.desc()).all())
    return [{"id": r.id, "goal": r.goal, "timeline": r.timeline,
             "created_at": r.created_at.isoformat()} for r in rows]


@router.get("/{roadmap_id}")
def get_roadmap(roadmap_id: str, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    r = db.get(Roadmap, roadmap_id)
    if r is None or r.user_id != user.id:
        raise HTTPException(status_code=404, detail="Roadmap not found")
    return {"id": r.id, **json.loads(r.data)}


@router.delete("/{roadmap_id}", status_code=204)
def delete_roadmap(roadmap_id: str, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    r = db.get(Roadmap, roadmap_id)
    if r is None or r.user_id != user.id:
        raise HTTPException(status_code=404, detail="Roadmap not found")
    db.delete(r)
    db.commit()


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
