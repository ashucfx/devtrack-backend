import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_active_user
from app.api.dependencies.database import get_db
from app.models.user import User
from app.schemas.common import ErrorResponse, PaginatedResponse
from app.schemas.company import CompanyCreate, CompanyRead, CompanyUpdate
from app.services.company_service import CompanyService

router = APIRouter(prefix="/companies", tags=["Companies"])


@router.post(
    "",
    response_model=CompanyRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new company record",
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        409: {"model": ErrorResponse, "description": "Company name already exists for user"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def create_company(
    company_in: CompanyCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> CompanyRead:
    """Create a new company record scoped to the authenticated user."""
    service = CompanyService(db)
    company = await service.create_company(company_in, current_user.id)
    return CompanyRead.model_validate(company)


@router.get(
    "",
    response_model=PaginatedResponse[CompanyRead],
    status_code=status.HTTP_200_OK,
    summary="List user companies with search and pagination",
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
    },
)
async def list_companies(
    search: str | None = Query(default=None, description="Search by name, industry, or location"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[CompanyRead]:
    """Retrieve paginated list of companies owned by the current user."""
    service = CompanyService(db)
    return await service.list_companies(
        user_id=current_user.id,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{company_id}",
    response_model=CompanyRead,
    status_code=status.HTTP_200_OK,
    summary="Get company by ID",
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Company not found or access denied"},
    },
)
async def get_company(
    company_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> CompanyRead:
    """Retrieve details of a single company owned by the user."""
    service = CompanyService(db)
    company = await service.get_company(company_id, current_user.id)
    return CompanyRead.model_validate(company)


@router.patch(
    "/{company_id}",
    response_model=CompanyRead,
    status_code=status.HTTP_200_OK,
    summary="Update company details",
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Company not found or access denied"},
        409: {"model": ErrorResponse, "description": "Company name conflict"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def update_company(
    company_id: uuid.UUID,
    company_update: CompanyUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> CompanyRead:
    """Update an existing company owned by the user."""
    service = CompanyService(db)
    company = await service.update_company(company_id, company_update, current_user.id)
    return CompanyRead.model_validate(company)


@router.delete(
    "/{company_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete company",
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Company not found or access denied"},
    },
)
async def delete_company(
    company_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a company record owned by the user."""
    service = CompanyService(db)
    await service.delete_company(company_id, current_user.id)
