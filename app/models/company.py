import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.user import User


class Company(Base, UUIDMixin, TimestampMixin):
    """Company entity representing an employer associated with a user's job search."""

    __tablename__ = "companies"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True).with_variant(PG_UUID(as_uuid=True), "postgresql"),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    website: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    industry: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    location: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    user: Mapped["User"] = relationship(
        "User",
        back_populates="companies",
    )
    applications: Mapped[list["Application"]] = relationship(
        "Application",
        back_populates="company",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_companies_user_id_name"),
        Index("ix_companies_user_name", "user_id", "name"),
        Index("ix_companies_user_industry", "user_id", "industry"),
    )
