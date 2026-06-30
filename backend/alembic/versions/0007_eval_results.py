"""eval_results — persisted LLM-as-judge evaluations

Revision ID: 0007_eval_results
Revises: 0006_roadmaps_materials_mastery
Create Date: 2026-06-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0007_eval_results"
down_revision: Union[str, None] = "0006_roadmaps_materials_mastery"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "eval_results",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_eval_results_user_id"), "eval_results", ["user_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_eval_results_user_id"), table_name="eval_results")
    op.drop_table("eval_results")
