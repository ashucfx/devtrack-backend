import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.core.constants import InterviewStatus, InterviewType
from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.user import User


class Interview(Base, UUIDMixin, TimestampMixin):
    """Interview round entity associated with a job application."""

    __tablename__ = "interviews"

    application_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True).with_variant(PG_UUID(as_uuid=True), "postgresql"),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True).with_variant(PG_UUID(as_uuid=True), "postgresql"),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    round_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    interview_type: Mapped[str] = mapped_column(
        String(50),
        default=InterviewType.TECHNICAL,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    duration_minutes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    meeting_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    interviewer_names: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default=InterviewStatus.SCHEDULED,
        nullable=False,
    )
    feedback: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    application: Mapped["Application"] = relationship(
        "Application",
        back_populates="interviews",
    )
    user: Mapped["User"] = relationship(
        "User",
        back_populates="interviews",
    )

    __table_args__ = (
        Index("ix_interviews_user_status_scheduled", "user_id", "status", "scheduled_at"),
        Index("ix_interviews_app_round", "application_id", "round_number"),
    )
