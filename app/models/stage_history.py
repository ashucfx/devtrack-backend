import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.models.base import Base, TimestampMixin, UUIDMixin, utc_now

if TYPE_CHECKING:
    from app.models.application import Application


class ApplicationStageHistory(Base, UUIDMixin, TimestampMixin):
    """Append-only historical audit ledger recording all application stage transitions."""

    __tablename__ = "application_stage_history"

    application_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True).with_variant(PG_UUID(as_uuid=True), "postgresql"),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_stage: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    to_stage: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
        index=True,
    )

    application: Mapped["Application"] = relationship(
        "Application",
        back_populates="stage_history",
    )

    __table_args__ = (Index("ix_stage_history_app_changed", "application_id", "changed_at"),)
