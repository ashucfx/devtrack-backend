"""Create follow_ups table

Revision ID: 006_follow_ups
Revises: 005_interviews_notes
Create Date: 2026-09-20 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "006_follow_ups"
down_revision: str | None = "005_interviews_notes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "follow_ups",
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
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
            name=op.f("fk_follow_ups_application_id_applications"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_follow_ups_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_follow_ups")),
    )
    op.create_index(
        op.f("ix_follow_ups_application_id"),
        "follow_ups",
        ["application_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_follow_ups_user_id"),
        "follow_ups",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_follow_ups_due_date"),
        "follow_ups",
        ["due_date"],
        unique=False,
    )
    op.create_index(
        "ix_followups_user_status_due",
        "follow_ups",
        ["user_id", "status", "due_date"],
        unique=False,
    )
    op.create_index(
        "ix_followups_app_due",
        "follow_ups",
        ["application_id", "due_date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_followups_app_due", table_name="follow_ups")
    op.drop_index("ix_followups_user_status_due", table_name="follow_ups")
    op.drop_index(op.f("ix_follow_ups_due_date"), table_name="follow_ups")
    op.drop_index(op.f("ix_follow_ups_user_id"), table_name="follow_ups")
    op.drop_index(op.f("ix_follow_ups_application_id"), table_name="follow_ups")
    op.drop_table("follow_ups")
