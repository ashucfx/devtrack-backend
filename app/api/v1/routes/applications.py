import uuid
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_active_user
from app.api.dependencies.database import get_db
from app.core.constants import (
    ApplicationStage,
    ApplicationStatus,
    EmploymentType,
    LocationType,
    Priority,
)
from app.models.user import User
from app.schemas.application import ApplicationCreate, ApplicationRead, ApplicationUpdate
from app.schemas.common import ErrorResponse, PaginatedResponse
from app.schemas.stage_history import ApplicationTimelineResponse, StageTransitionRequest
from app.services.application_service import ApplicationService

router = APIRouter(prefix="/applications", tags=["Applications"])


@router.post(
    "",
    response_model=ApplicationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new job application",
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Referenced company not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def create_application(
    application_in: ApplicationCreate,
    _idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ApplicationRead:
    """Create a new job application linked to a company owned by the user."""
    service = ApplicationService(db)
    application = await service.create_application(application_in, current_user.id)
    return ApplicationRead.model_validate(application)


@router.get(
    "",
    response_model=PaginatedResponse[ApplicationRead],
    status_code=status.HTTP_200_OK,
    summary="List job applications with filtering, sorting, and pagination",
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
    },
)
async def list_applications(
    status_filter: ApplicationStatus | None = Query(
        default=None, alias="status", description="Filter by status (ACTIVE, ARCHIVED)"
    ),
    stage: ApplicationStage | None = Query(
        default=None, description="Filter by stage (SAVED, APPLIED, INTERVIEW, OFFER, etc)"
    ),
    company_id: uuid.UUID | None = Query(default=None, description="Filter by company ID"),
    priority: Priority | None = Query(default=None, description="Filter by priority"),
    employment_type: EmploymentType | None = Query(
        default=None, description="Filter by employment type"
    ),
    location_type: LocationType | None = Query(default=None, description="Filter by location type"),
    search: str | None = Query(
        default=None, description="Search term matching job title, company name, or location"
    ),
    date_from: date | None = Query(
        default=None, description="Filter applied date >= date_from (YYYY-MM-DD)"
    ),
    date_to: date | None = Query(
        default=None, description="Filter applied date <= date_to (YYYY-MM-DD)"
    ),
    sort_by: Literal[
        "applied_date", "created_at", "job_title", "priority", "salary_max", "company_name"
    ] = Query(default="applied_date", description="Field to sort by"),
    sort_order: Literal["asc", "desc"] = Query(default="desc", description="Sort order"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ApplicationRead]:
    """Retrieve filtered, sorted, and paginated job applications owned by the user."""
    service = ApplicationService(db)
    return await service.list_applications(
        user_id=current_user.id,
        status=status_filter.value if status_filter else None,
        stage=stage.value if stage else None,
        company_id=company_id,
        priority=priority.value if priority else None,
        employment_type=employment_type.value if employment_type else None,
        location_type=location_type.value if location_type else None,
        search=search,
        date_from=date_from,
        date_to=date_to,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{application_id}",
    response_model=ApplicationRead,
    status_code=status.HTTP_200_OK,
    summary="Get job application by ID",
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Application not found or access denied"},
    },
)
async def get_application(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ApplicationRead:
    """Retrieve details of a single job application owned by the user."""
    service = ApplicationService(db)
    application = await service.get_application(application_id, current_user.id)
    return ApplicationRead.model_validate(application)


@router.patch(
    "/{application_id}",
    response_model=ApplicationRead,
    status_code=status.HTTP_200_OK,
    summary="Update job application details",
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Application or company not found"},
        422: {
            "model": ErrorResponse,
            "description": "Validation error or invalid state transition",
        },
    },
)
async def update_application(
    application_id: uuid.UUID,
    app_update: ApplicationUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ApplicationRead:
    """Update fields on an existing job application owned by the user."""
    service = ApplicationService(db)
    application = await service.update_application(application_id, app_update, current_user.id)
    return ApplicationRead.model_validate(application)


@router.post(
    "/{application_id}/stage",
    response_model=ApplicationRead,
    status_code=status.HTTP_200_OK,
    summary="Transition application stage",
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Application not found or access denied"},
        422: {"model": ErrorResponse, "description": "Illegal stage transition"},
    },
)
async def transition_application_stage(
    application_id: uuid.UUID,
    transition_in: StageTransitionRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ApplicationRead:
    """Transition an application to a new stage enforcing finite state machine constraints."""
    service = ApplicationService(db)
    application = await service.transition_stage(
        application_id=application_id,
        to_stage=transition_in.to_stage,
        notes=transition_in.notes,
        user_id=current_user.id,
    )
    return ApplicationRead.model_validate(application)


@router.get(
    "/{application_id}/timeline",
    response_model=ApplicationTimelineResponse,
    status_code=status.HTTP_200_OK,
    summary="Get application stage transition timeline",
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Application not found or access denied"},
    },
)
async def get_application_timeline(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ApplicationTimelineResponse:
    """Retrieve the complete chronological stage progression audit trail."""
    service = ApplicationService(db)
    return await service.get_application_timeline(application_id, current_user.id)


@router.delete(
    "/{application_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete job application",
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Application not found or access denied"},
    },
)
async def delete_application(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a job application record owned by the user."""
    service = ApplicationService(db)
    await service.delete_application(application_id, current_user.id)
