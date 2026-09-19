import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.core.constants import (
    ApplicationSource,
    ApplicationStage,
    ApplicationStatus,
    EmploymentType,
    LocationType,
    Priority,
)
from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.interview import Interview
    from app.models.stage_history import ApplicationStageHistory
    from app.models.user import User


class Application(Base, UUIDMixin, TimestampMixin):
    """Core job application entity tracking status, stages, and metadata."""

    __tablename__ = "applications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True).with_variant(PG_UUID(as_uuid=True), "postgresql"),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True).with_variant(PG_UUID(as_uuid=True), "postgresql"),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_title: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    job_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    employment_type: Mapped[str] = mapped_column(
        String(50),
        default=EmploymentType.FULL_TIME,
        nullable=False,
    )
    location: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    location_type: Mapped[str] = mapped_column(
        String(50),
        default=LocationType.REMOTE,
        nullable=False,
    )
    salary_min: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )
    salary_max: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        default="USD",
        nullable=False,
    )
    source: Mapped[str] = mapped_column(
        String(50),
        default=ApplicationSource.LINKEDIN,
        nullable=False,
    )
    applied_date: Mapped[date] = mapped_column(
        Date,
        default=date.today,
        nullable=False,
        index=True,
    )
    current_stage: Mapped[str] = mapped_column(
        String(50),
        default=ApplicationStage.APPLIED,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default=ApplicationStatus.ACTIVE,
        nullable=False,
    )
    priority: Mapped[str] = mapped_column(
        String(50),
        default=Priority.MEDIUM,
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    user: Mapped["User"] = relationship(
        "User",
        back_populates="applications",
    )
    company: Mapped["Company"] = relationship(
        "Company",
        back_populates="applications",
        lazy="joined",
    )
    stage_history: Mapped[list["ApplicationStageHistory"]] = relationship(
        "ApplicationStageHistory",
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="ApplicationStageHistory.changed_at.asc()",
        lazy="selectin",
    )
    interviews: Mapped[list["Interview"]] = relationship(
        "Interview",
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="Interview.round_number.asc()",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_applications_user_status_stage", "user_id", "status", "current_stage"),
        Index("ix_applications_user_applied_date", "user_id", "applied_date"),
    )
