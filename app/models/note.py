import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.core.constants import EntityType
from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


class Note(Base, UUIDMixin, TimestampMixin):
    """Polymorphic rich contextual note attached to applications, companies, or interviews."""

    __tablename__ = "notes"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True).with_variant(PG_UUID(as_uuid=True), "postgresql"),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entity_type: Mapped[str] = mapped_column(
        String(50),
        default=EntityType.APPLICATION,
        nullable=False,
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True).with_variant(PG_UUID(as_uuid=True), "postgresql"),
        nullable=False,
        index=True,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    user: Mapped["User"] = relationship(
        "User",
        back_populates="notes",
    )

    __table_args__ = (
        Index("ix_notes_user_entity", "user_id", "entity_type", "entity_id"),
        Index("ix_notes_entity_lookup", "entity_type", "entity_id"),
    )
