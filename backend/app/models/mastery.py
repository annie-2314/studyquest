"""Knowledge-tracing state: per-learner, per-concept mastery (Bayesian Knowledge
Tracing) plus a time-series of mastery events for the Insights chart.

`p_known` is the BKT probability the learner has mastered the concept (0..1).
`due_at` drives a lightweight spaced-review queue.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class LearnerConceptMastery(Base):
    __tablename__ = "learner_concept_mastery"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False, index=True)
    concept: Mapped[str] = mapped_column(String, nullable=False, index=True)
    p_known: Mapped[float] = mapped_column(Float, default=0.0)   # BKT mastery 0..1
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    correct: Mapped[int] = mapped_column(Integer, default=0)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)  # next review


class MasteryEvent(Base):
    __tablename__ = "mastery_events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False, index=True)
    concept: Mapped[str] = mapped_column(String, nullable=False)
    p_known: Mapped[float] = mapped_column(Float, nullable=False)
    correct: Mapped[int] = mapped_column(Integer, default=0)  # 1/0 — was this attempt correct
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
