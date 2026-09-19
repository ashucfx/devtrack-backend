import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_active_user
from app.api.dependencies.database import get_db
from app.models.user import User
from app.schemas.common import ErrorResponse
from app.schemas.interview import InterviewCreate, InterviewRead, InterviewUpdate
from app.services.interview_service import InterviewService

router = APIRouter(tags=["Interviews"])


@router.post(
    "/applications/{application_id}/interviews",
    response_model=InterviewRead,
    status_code=status.HTTP_201_CREATED,
    summary="Schedule an interview round for an application",
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Application not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def create_interview(
    application_id: uuid.UUID,
    interview_in: InterviewCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> InterviewRead:
    """Schedule a new interview round for an application owned by the user."""
    service = InterviewService(db)
    interview = await service.create_interview(application_id, current_user.id, interview_in)
    return InterviewRead.model_validate(interview)


@router.get(
    "/applications/{application_id}/interviews",
    response_model=list[InterviewRead],
    status_code=status.HTTP_200_OK,
    summary="List all interview rounds for an application",
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Application not found"},
    },
)
async def list_interviews_for_application(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[InterviewRead]:
    """Retrieve all interview rounds for an application ordered by round number."""
    service = InterviewService(db)
    interviews = await service.list_interviews(application_id, current_user.id)
    return [InterviewRead.model_validate(item) for item in interviews]


@router.get(
    "/interviews/{interview_id}",
    response_model=InterviewRead,
    status_code=status.HTTP_200_OK,
    summary="Get interview round details by ID",
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Interview not found"},
    },
)
async def get_interview(
    interview_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> InterviewRead:
    """Retrieve details of an interview round enforcing user isolation."""
    service = InterviewService(db)
    interview = await service.get_interview(interview_id, current_user.id)
    return InterviewRead.model_validate(interview)


@router.patch(
    "/interviews/{interview_id}",
    response_model=InterviewRead,
    status_code=status.HTTP_200_OK,
    summary="Update an interview round",
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Interview not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def update_interview(
    interview_id: uuid.UUID,
    interview_update: InterviewUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> InterviewRead:
    """Update details or status of an interview round."""
    service = InterviewService(db)
    interview = await service.update_interview(interview_id, current_user.id, interview_update)
    return InterviewRead.model_validate(interview)


@router.delete(
    "/interviews/{interview_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an interview round",
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Interview not found"},
    },
)
async def delete_interview(
    interview_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete an interview round enforcing user isolation."""
    service = InterviewService(db)
    await service.delete_interview(interview_id, current_user.id)
