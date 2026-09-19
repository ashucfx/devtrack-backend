import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.note import Note
from app.repositories.base import BaseRepository


class NoteRepository(BaseRepository[Note]):
    """Repository handling polymorphic notes attached to tracked entities."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Note, session)

    async def get_by_id_and_user(self, note_id: uuid.UUID, user_id: uuid.UUID) -> Note | None:
        """Fetch a note by ID enforcing user isolation."""
        stmt = select(Note).where(
            Note.id == note_id,
            Note.user_id == user_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_entity(
        self, entity_type: str, entity_id: uuid.UUID, user_id: uuid.UUID
    ) -> Sequence[Note]:
        """Fetch all notes for a specific entity and user ordered newest first."""
        stmt = (
            select(Note)
            .where(
                Note.entity_type == entity_type,
                Note.entity_id == entity_id,
                Note.user_id == user_id,
            )
            .order_by(Note.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_by_user(
        self,
        user_id: uuid.UUID,
        entity_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Note]:
        """Fetch all notes belonging to a user with optional entity type filter."""
        stmt = select(Note).where(Note.user_id == user_id)
        if entity_type:
            stmt = stmt.where(Note.entity_type == entity_type)
        stmt = stmt.order_by(Note.created_at.desc()).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()
