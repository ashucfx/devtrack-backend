import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_active_user
from app.api.dependencies.database import get_db
from app.core.constants import EntityType
from app.models.user import User
from app.schemas.common import ErrorResponse
from app.schemas.note import NoteCreate, NoteRead
from app.services.note_service import NoteService

router = APIRouter(prefix="/notes", tags=["Notes"])


@router.post(
    "",
    response_model=NoteRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a note attached to an entity",
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Target parent entity not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def create_note(
    note_in: NoteCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> NoteRead:
    """Create a rich contextual note attached to a user's company, application, or interview."""
    service = NoteService(db)
    note = await service.create_note(current_user.id, note_in)
    return NoteRead.model_validate(note)


@router.get(
    "",
    response_model=list[NoteRead],
    status_code=status.HTTP_200_OK,
    summary="List notes attached to an entity",
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Target parent entity not found"},
    },
)
async def list_notes(
    entity_type: EntityType = Query(
        ..., description="Type of entity (APPLICATION, COMPANY, INTERVIEW)"
    ),
    entity_id: uuid.UUID = Query(..., description="ID of the parent entity"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[NoteRead]:
    """Retrieve all notes attached to a specific entity owned by the user."""
    service = NoteService(db)
    notes = await service.list_notes_for_entity(entity_type, entity_id, current_user.id)
    return [NoteRead.model_validate(item) for item in notes]


@router.delete(
    "/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a note",
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Note not found"},
    },
)
async def delete_note(
    note_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a note enforcing user isolation."""
    service = NoteService(db)
    await service.delete_note(note_id, current_user.id)
