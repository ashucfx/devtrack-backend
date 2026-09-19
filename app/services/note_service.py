import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import EntityType
from app.core.exceptions import EntityNotFoundException, ValidationException
from app.models.note import Note
from app.repositories.application_repository import ApplicationRepository
from app.repositories.company_repository import CompanyRepository
from app.repositories.interview_repository import InterviewRepository
from app.repositories.note_repository import NoteRepository
from app.schemas.note import NoteCreate


class NoteService:
    """Service handling polymorphic notes with multi-tenant parent verification."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.note_repo = NoteRepository(session)
        self.application_repo = ApplicationRepository(session)
        self.company_repo = CompanyRepository(session)
        self.interview_repo = InterviewRepository(session)

    async def _verify_parent_entity_access(
        self, entity_type: str, entity_id: uuid.UUID, user_id: uuid.UUID
    ) -> None:
        """Verify that the target parent entity exists and belongs to the authenticated user."""
        match entity_type:
            case EntityType.APPLICATION:
                parent = await self.application_repo.get_by_id_and_user(entity_id, user_id)
            case EntityType.COMPANY:
                parent = await self.company_repo.get_by_id_and_user(entity_id, user_id)
            case EntityType.INTERVIEW:
                parent = await self.interview_repo.get_by_id_and_user(entity_id, user_id)
            case _:
                raise ValidationException(
                    f"Unsupported entity type for notes: '{entity_type}'",
                    errors=[{"field": "entity_type", "message": "Unsupported entity type"}],
                )

        if not parent:
            raise EntityNotFoundException(str(entity_type).capitalize(), entity_id)

    async def create_note(self, user_id: uuid.UUID, note_in: NoteCreate) -> Note:
        """Attach a new note to a verified tenant-owned entity."""
        await self._verify_parent_entity_access(note_in.entity_type, note_in.entity_id, user_id)

        note = Note(
            user_id=user_id,
            entity_type=note_in.entity_type,
            entity_id=note_in.entity_id,
            content=note_in.content.strip(),
        )
        note = await self.note_repo.create(note)
        await self.session.commit()
        return note

    async def list_notes_for_entity(
        self, entity_type: str, entity_id: uuid.UUID, user_id: uuid.UUID
    ) -> Sequence[Note]:
        """Fetch all notes for a parent entity after verifying tenant ownership."""
        await self._verify_parent_entity_access(entity_type, entity_id, user_id)
        return await self.note_repo.list_by_entity(entity_type, entity_id, user_id)

    async def delete_note(self, note_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """Delete a note enforcing tenant isolation."""
        note = await self.note_repo.get_by_id_and_user(note_id, user_id)
        if not note:
            raise EntityNotFoundException("Note", note_id)
        await self.note_repo.delete(note)
        await self.session.commit()
