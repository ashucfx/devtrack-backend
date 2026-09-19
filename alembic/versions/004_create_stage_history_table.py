"""Create application_stage_history table

Revision ID: 004_stage_history
Revises: 003_applications
Create Date: 2026-09-20 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004_stage_history"
down_revision: str | None = "003_applications"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "application_stage_history",
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
        sa.Column("from_stage", sa.String(length=50), nullable=True),
        sa.Column("to_stage", sa.String(length=50), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
            name=op.f("fk_application_stage_history_application_id_applications"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_application_stage_history")),
    )
    op.create_index(
        op.f("ix_application_stage_history_application_id"),
        "application_stage_history",
        ["application_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_application_stage_history_changed_at"),
        "application_stage_history",
        ["changed_at"],
        unique=False,
    )
    op.create_index(
        "ix_stage_history_app_changed",
        "application_stage_history",
        ["application_id", "changed_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_stage_history_app_changed", table_name="application_stage_history")
    op.drop_index(
        op.f("ix_application_stage_history_changed_at"), table_name="application_stage_history"
    )
    op.drop_index(
        op.f("ix_application_stage_history_application_id"), table_name="application_stage_history"
    )
    op.drop_table("application_stage_history")
