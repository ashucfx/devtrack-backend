"""Create companies table

Revision ID: 002_companies
Revises: 001_auth_users
Create Date: 2026-09-20 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002_companies"
down_revision: str | None = "001_auth_users"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "companies",
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
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("website", sa.String(length=255), nullable=True),
        sa.Column("industry", sa.String(length=100), nullable=True),
        sa.Column("location", sa.String(length=100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_companies_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_companies")),
        sa.UniqueConstraint("user_id", "name", name="uq_companies_user_id_name"),
    )
    op.create_index(op.f("ix_companies_user_id"), "companies", ["user_id"], unique=False)
    op.create_index("ix_companies_user_name", "companies", ["user_id", "name"], unique=False)
    op.create_index(
        "ix_companies_user_industry", "companies", ["user_id", "industry"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_companies_user_industry", table_name="companies")
    op.drop_index("ix_companies_user_name", table_name="companies")
    op.drop_index(op.f("ix_companies_user_id"), table_name="companies")
    op.drop_table("companies")
