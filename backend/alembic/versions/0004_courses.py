"""courses — courses and course_steps

Revision ID: 0004_courses
Revises: 0003_rag
Create Date: 2026-06-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004_courses"
down_revision: Union[str, None] = "0003_rag"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "courses",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("playlist_url", sa.String(), nullable=False),
        sa.Column("total_seconds", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_courses_user_id"), "courses", ["user_id"])

    op.create_table(
        "course_steps",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("course_id", sa.String(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("video_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("completed", sa.Boolean(), nullable=False),
        sa.Column("quiz_passed", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_course_steps_course_id"), "course_steps", ["course_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_course_steps_course_id"), table_name="course_steps")
    op.drop_table("course_steps")
    op.drop_index(op.f("ix_courses_user_id"), table_name="courses")
    op.drop_table("courses")
