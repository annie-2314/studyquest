"""roadmaps + grounded-RAG materials + knowledge-tracing mastery

Revision ID: 0006_roadmaps_materials_mastery
Revises: 0005_game
Create Date: 2026-06-26

Adds: roadmaps (saved learning paths), materials + material_chunks (embedded
grounded-RAG sources), learner_concept_mastery + mastery_events (BKT).
Non-destructive — only creates tables.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0006_roadmaps_materials_mastery"
down_revision: Union[str, None] = "0005_game"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "roadmaps",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("goal", sa.String(), nullable=False),
        sa.Column("hours_per_week", sa.Integer(), nullable=True),
        sa.Column("timeline", sa.String(), nullable=True),
        sa.Column("language", sa.String(), nullable=True),
        sa.Column("data", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_roadmaps_user_id"), "roadmaps", ["user_id"])

    op.create_table(
        "materials",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_materials_user_id"), "materials", ["user_id"])

    op.create_table(
        "material_chunks",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("material_id", sa.String(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("page", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("concept_tags", sa.String(), nullable=True),
        sa.Column("embedding", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["material_id"], ["materials.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_material_chunks_material_id"), "material_chunks", ["material_id"])

    op.create_table(
        "learner_concept_mastery",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("concept", sa.String(), nullable=False),
        sa.Column("p_known", sa.Float(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=True),
        sa.Column("correct", sa.Integer(), nullable=True),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_learner_concept_mastery_user_id"), "learner_concept_mastery", ["user_id"])
    op.create_index(op.f("ix_learner_concept_mastery_concept"), "learner_concept_mastery", ["concept"])

    op.create_table(
        "mastery_events",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("concept", sa.String(), nullable=False),
        sa.Column("p_known", sa.Float(), nullable=False),
        sa.Column("correct", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_mastery_events_user_id"), "mastery_events", ["user_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_mastery_events_user_id"), table_name="mastery_events")
    op.drop_table("mastery_events")
    op.drop_index(op.f("ix_learner_concept_mastery_concept"), table_name="learner_concept_mastery")
    op.drop_index(op.f("ix_learner_concept_mastery_user_id"), table_name="learner_concept_mastery")
    op.drop_table("learner_concept_mastery")
    op.drop_index(op.f("ix_material_chunks_material_id"), table_name="material_chunks")
    op.drop_table("material_chunks")
    op.drop_index(op.f("ix_materials_user_id"), table_name="materials")
    op.drop_table("materials")
    op.drop_index(op.f("ix_roadmaps_user_id"), table_name="roadmaps")
    op.drop_table("roadmaps")
