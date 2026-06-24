"""Phase 4 models: a course (from a YouTube playlist) and its ordered steps."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    playlist_url: Mapped[str] = mapped_column(String, nullable=False)
    total_seconds: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    steps: Mapped[list["CourseStep"]] = relationship(
        back_populates="course", cascade="all, delete-orphan", order_by="CourseStep.ordinal")


class CourseStep(Base):
    __tablename__ = "course_steps"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    course_id: Mapped[str] = mapped_column(String, ForeignKey("courses.id"), nullable=False, index=True)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    video_id: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    quiz_passed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    course: Mapped["Course"] = relationship(back_populates="steps")
