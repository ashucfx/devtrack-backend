"""Create interviews and notes tables

Revision ID: 005_interviews_notes
Revises: 004_stage_history
Create Date: 2026-09-20 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "005_interviews_notes"
down_revision: str | None = "004_stage_history"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "interviews",
        sa.Column(
            "id",
            sa.Uuid().with_variant(postgresql.UUID(as_uuid=True), "postgresql"),
            nullable=False,
        ),
        sa.Column(
            "application_id",
            sa.Uuid().with_variant(postgresql.UUID(as_uuid=True), "postgresql"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Uuid().with_variant(postgresql.UUID(as_uuid=True), "postgresql"),
            nullable=False,
        ),
        sa.Column("round_number", sa.Integer(), nullable=False),
        sa.Column("interview_type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("meeting_url", sa.String(length=500), nullable=True),
        sa.Column("interviewer_names", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
            name=op.f("fk_interviews_application_id_applications"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_interviews_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_interviews")),
    )
    op.create_index(
        op.f("ix_interviews_application_id"),
        "interviews",
        ["application_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_interviews_user_id"),
        "interviews",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_interviews_scheduled_at"),
        "interviews",
        ["scheduled_at"],
        unique=False,
    )
    op.create_index(
        "ix_interviews_user_status_scheduled",
        "interviews",
        ["user_id", "status", "scheduled_at"],
        unique=False,
    )
    op.create_index(
        "ix_interviews_app_round",
        "interviews",
        ["application_id", "round_number"],
        unique=False,
    )

    op.create_table(
        "notes",
        sa.Column(
            "id",
            sa.Uuid().with_variant(postgresql.UUID(as_uuid=True), "postgresql"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Uuid().with_variant(postgresql.UUID(as_uuid=True), "postgresql"),
            nullable=False,
        ),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column(
            "entity_id",
            sa.Uuid().with_variant(postgresql.UUID(as_uuid=True), "postgresql"),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_notes_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notes")),
    )
    op.create_index(
        op.f("ix_notes_user_id"),
        "notes",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_notes_entity_id"),
        "notes",
        ["entity_id"],
        unique=False,
    )
    op.create_index(
        "ix_notes_user_entity",
        "notes",
        ["user_id", "entity_type", "entity_id"],
        unique=False,
    )
    op.create_index(
        "ix_notes_entity_lookup",
        "notes",
        ["entity_type", "entity_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_notes_entity_lookup", table_name="notes")
    op.drop_index("ix_notes_user_entity", table_name="notes")
    op.drop_index(op.f("ix_notes_entity_id"), table_name="notes")
    op.drop_index(op.f("ix_notes_user_id"), table_name="notes")
    op.drop_table("notes")

    op.drop_index("ix_interviews_app_round", table_name="interviews")
    op.drop_index("ix_interviews_user_status_scheduled", table_name="interviews")
    op.drop_index(op.f("ix_interviews_scheduled_at"), table_name="interviews")
    op.drop_index(op.f("ix_interviews_user_id"), table_name="interviews")
    op.drop_index(op.f("ix_interviews_application_id"), table_name="interviews")
    op.drop_table("interviews")
