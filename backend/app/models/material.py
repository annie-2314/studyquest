"""Grounded-RAG materials: a student-uploaded source (PDF / notes / URL / video)
and its embedded chunks.

This is separate from the Phase-3 `Document`/`DocChunk` (BM25) store — it's the
embeddings-based pipeline that powers cited answers. The chunk embedding is kept
as a JSON list of floats (portable across SQLite/Postgres, no extension needed);
retrieval loads a material's chunks and ranks them with NumPy cosine similarity.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import settings
from app.database import Base


def _embedding_column_type():
    """vector(N) on pgvector, else TEXT (JSON list of floats) for portability/SQLite."""
    if settings.vector_backend == "pgvector":
        try:
            from pgvector.sqlalchemy import Vector
            return Vector(settings.embedding_dim)
        except Exception:
            return Text
    return Text


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Material(Base):
    __tablename__ = "materials"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    kind: Mapped[str] = mapped_column(String, default="text")  # text | pdf | url | video
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    chunks: Mapped[list["MaterialChunk"]] = relationship(
        back_populates="material", cascade="all, delete-orphan", order_by="MaterialChunk.ordinal")


class MaterialChunk(Base):
    __tablename__ = "material_chunks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    material_id: Mapped[str] = mapped_column(String, ForeignKey("materials.id"), nullable=False, index=True)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    page: Mapped[int] = mapped_column(Integer, default=0)         # source page (PDFs)
    source: Mapped[str] = mapped_column(String, default="")        # citation handle, e.g. "notes p.12"
    concept_tags: Mapped[str] = mapped_column(String, default="")  # comma-separated tags
    # TEXT JSON (numpy backend) or pgvector vector(dim) (pgvector backend).
    embedding: Mapped[object] = mapped_column(_embedding_column_type(), nullable=False)

    material: Mapped["Material"] = relationship(back_populates="chunks")
