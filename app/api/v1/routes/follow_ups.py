import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_active_user
from app.api.dependencies.database import get_db
from app.core.constants import FollowUpStatus
from app.models.user import User
from app.schemas.common import ErrorResponse
from app.schemas.follow_up import FollowUpCreate, FollowUpRead, FollowUpUpdate
from app.services.follow_up_service import FollowUpService

router = APIRouter(tags=["Follow-ups"])


@router.post(
    "/applications/{application_id}/follow-ups",
    response_model=FollowUpRead,
    status_code=status.HTTP_201_CREATED,
    summary="Schedule a follow-up task for an application",
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Application not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def create_follow_up(
    application_id: uuid.UUID,
    follow_up_in: FollowUpCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> FollowUpRead:
    """Create a new scheduled follow-up reminder for an application owned by the user."""
    service = FollowUpService(db)
    follow_up = await service.create_follow_up(application_id, current_user.id, follow_up_in)
    return FollowUpRead.model_validate(follow_up)


@router.get(
    "/applications/{application_id}/follow-ups",
    response_model=list[FollowUpRead],
    status_code=status.HTTP_200_OK,
    summary="List all follow-up tasks for an application",
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Application not found"},
    },
)
async def list_follow_ups_for_application(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[FollowUpRead]:
    """Retrieve all follow-up tasks for an application ordered by due date."""
    service = FollowUpService(db)
    follow_ups = await service.list_follow_ups_for_application(application_id, current_user.id)
    return [FollowUpRead.model_validate(item) for item in follow_ups]


@router.get(
    "/follow-ups",
    response_model=list[FollowUpRead],
    status_code=status.HTTP_200_OK,
    summary="List user follow-up tasks across all applications with timeframe filters",
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
    },
)
async def list_follow_ups(
    status_filter: FollowUpStatus | None = Query(
        default=None, alias="status", description="Filter by status (PENDING, COMPLETED, CANCELLED)"
    ),
    timeframe: Literal["today", "overdue", "upcoming"] | None = Query(
        default=None,
        description="Filter by relative timeframe (today, overdue, upcoming)",
    ),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[FollowUpRead]:
    """Retrieve scheduled follow-ups across all applications for the authenticated user."""
    service = FollowUpService(db)
    follow_ups = await service.list_follow_ups(
        user_id=current_user.id,
        status=status_filter.value if status_filter else None,
        timeframe=timeframe,
    )
    return [FollowUpRead.model_validate(item) for item in follow_ups]


@router.get(
    "/follow-ups/{follow_up_id}",
    response_model=FollowUpRead,
    status_code=status.HTTP_200_OK,
    summary="Get follow-up details by ID",
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "FollowUp not found"},
    },
)
async def get_follow_up(
    follow_up_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> FollowUpRead:
    """Retrieve details of a single follow-up task enforcing user isolation."""
    service = FollowUpService(db)
    follow_up = await service.get_follow_up(follow_up_id, current_user.id)
    return FollowUpRead.model_validate(follow_up)


@router.patch(
    "/follow-ups/{follow_up_id}",
    response_model=FollowUpRead,
    status_code=status.HTTP_200_OK,
    summary="Update follow-up task details or mark complete",
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "FollowUp not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def update_follow_up(
    follow_up_id: uuid.UUID,
    follow_up_update: FollowUpUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> FollowUpRead:
    """Update follow-up details or toggle completion status."""
    service = FollowUpService(db)
    follow_up = await service.update_follow_up(follow_up_id, current_user.id, follow_up_update)
    return FollowUpRead.model_validate(follow_up)


@router.delete(
    "/follow-ups/{follow_up_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a follow-up task",
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "FollowUp not found"},
    },
)
async def delete_follow_up(
    follow_up_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a follow-up task enforcing user isolation."""
    service = FollowUpService(db)
    await service.delete_follow_up(follow_up_id, current_user.id)
