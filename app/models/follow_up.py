import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.core.constants import FollowUpStatus
from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.user import User


class FollowUp(Base, UUIDMixin, TimestampMixin):
    """Scheduled task, reminder, or recruiter follow-up associated with an application."""

    __tablename__ = "follow_ups"

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
    title: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    due_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default=FollowUpStatus.PENDING,
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    application: Mapped["Application"] = relationship(
        "Application",
        back_populates="follow_ups",
    )
    user: Mapped["User"] = relationship(
        "User",
        back_populates="follow_ups",
    )

    __table_args__ = (
        Index("ix_followups_user_status_due", "user_id", "status", "due_date"),
        Index("ix_followups_app_due", "application_id", "due_date"),
    )
