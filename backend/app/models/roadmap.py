"""Saved learning roadmaps, so a learner can revisit ones they built before.

The generated roadmap (phases + resources + review notes) is stored as JSON in
`data` — it's a self-contained document we only ever read back whole, so a JSON
blob is simpler than spreading phases/resources across extra tables.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Roadmap(Base):
    __tablename__ = "roadmaps"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False, index=True)
    goal: Mapped[str] = mapped_column(String, nullable=False)
    hours_per_week: Mapped[int] = mapped_column(Integer, default=5)
    timeline: Mapped[str] = mapped_column(String, default="")
    language: Mapped[str] = mapped_column(String, default="")
    data: Mapped[str] = mapped_column(Text, nullable=False)  # full roadmap JSON
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
