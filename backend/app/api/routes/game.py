"""Phase 7 API: gamification profile, leaderboard, XP, and mini-games."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents import game_master
from app.api.deps import get_current_user
from app.database import get_db
from app.gamification import service
from app.models.user import User

router = APIRouter(prefix="/game", tags=["game"])


@router.get("/profile")
def profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return service.profile_json(db, service.get_profile(db, user.id))


@router.get("/leaderboard")
def leaderboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return service.leaderboard(db)


class XpIn(BaseModel):
    amount: int = service.XP_MINIGAME_WIN
    reason: str = "mini-game"


@router.post("/xp")
def add_xp(payload: XpIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Cap per-call XP so mini-games can't be abused to farm levels.
    amount = max(0, min(payload.amount, 50))
    return service.award_xp(db, user.id, amount, payload.reason)


class TopicIn(BaseModel):
    topic: str


@router.post("/flashcards")
def flashcards(payload: TopicIn, user: User = Depends(get_current_user)):
    return {"cards": game_master.flashcards(payload.topic)}


@router.post("/boss")
def boss(payload: TopicIn, user: User = Depends(get_current_user)):
    return {"questions": game_master.boss_quiz(payload.topic)}
