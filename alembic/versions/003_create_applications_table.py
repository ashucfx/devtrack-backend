"""Create applications table

Revision ID: 003_applications
Revises: 002_companies
Create Date: 2026-09-20 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003_applications"
down_revision: str | None = "002_companies"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "applications",
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
        sa.Column(
            "company_id",
            sa.Uuid().with_variant(postgresql.UUID(as_uuid=True), "postgresql"),
            nullable=False,
        ),
        sa.Column("job_title", sa.String(length=100), nullable=False),
        sa.Column("job_url", sa.String(length=500), nullable=True),
        sa.Column(
            "employment_type", sa.String(length=50), nullable=False, server_default="FULL_TIME"
        ),
        sa.Column("location", sa.String(length=100), nullable=True),
        sa.Column("location_type", sa.String(length=50), nullable=False, server_default="REMOTE"),
        sa.Column("salary_min", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("salary_max", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="USD"),
        sa.Column("source", sa.String(length=50), nullable=False, server_default="LINKEDIN"),
        sa.Column("applied_date", sa.Date(), nullable=False),
        sa.Column("current_stage", sa.String(length=50), nullable=False, server_default="APPLIED"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="ACTIVE"),
        sa.Column("priority", sa.String(length=50), nullable=False, server_default="MEDIUM"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name=op.f("fk_applications_company_id_companies"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_applications_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_applications")),
    )
    op.create_index(op.f("ix_applications_job_title"), "applications", ["job_title"], unique=False)
    op.create_index(
        op.f("ix_applications_applied_date"), "applications", ["applied_date"], unique=False
    )
    op.create_index(
        op.f("ix_applications_company_id"), "applications", ["company_id"], unique=False
    )
    op.create_index(op.f("ix_applications_user_id"), "applications", ["user_id"], unique=False)
    op.create_index(
        "ix_applications_user_status_stage",
        "applications",
        ["user_id", "status", "current_stage"],
        unique=False,
    )
    op.create_index(
        "ix_applications_user_applied_date",
        "applications",
        ["user_id", "applied_date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_applications_user_applied_date", table_name="applications")
    op.drop_index("ix_applications_user_status_stage", table_name="applications")
    op.drop_index(op.f("ix_applications_user_id"), table_name="applications")
    op.drop_index(op.f("ix_applications_company_id"), table_name="applications")
    op.drop_index(op.f("ix_applications_applied_date"), table_name="applications")
    op.drop_index(op.f("ix_applications_job_title"), table_name="applications")
    op.drop_table("applications")
