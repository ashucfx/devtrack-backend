from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_active_user
from app.api.dependencies.database import get_db
from app.models.user import User
from app.schemas.analytics import (
    BreakdownAnalyticsResponse,
    DashboardSummaryResponse,
    FunnelAnalyticsResponse,
    StageVelocityResponse,
    TimelineAnalyticsResponse,
)
from app.schemas.common import ErrorResponse
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get(
    "/dashboard",
    response_model=DashboardSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get overall dashboard KPIs and summary metrics",
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
    },
)
async def get_dashboard_summary(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardSummaryResponse:
    """Retrieve key metrics: active applications, response rate, offer rate, scheduled interviews."""
    service = AnalyticsService(db)
    return await service.get_dashboard_summary(current_user.id)


@router.get(
    "/funnel",
    response_model=FunnelAnalyticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get recruitment stage conversion funnel",
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
    },
)
async def get_funnel_analytics(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> FunnelAnalyticsResponse:
    """Retrieve application volume across stages with stage-over-stage conversion rates."""
    service = AnalyticsService(db)
    return await service.get_funnel_analytics(current_user.id)


@router.get(
    "/breakdown",
    response_model=BreakdownAnalyticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get application breakdowns by stage, source, location, and priority",
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
    },
)
async def get_breakdown_analytics(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> BreakdownAnalyticsResponse:
    """Retrieve multi-dimensional categorical distributions of job applications."""
    service = AnalyticsService(db)
    return await service.get_breakdown_analytics(current_user.id)


@router.get(
    "/velocity",
    response_model=StageVelocityResponse,
    status_code=status.HTTP_200_OK,
    summary="Get average transition velocity between recruitment stages",
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
    },
)
async def get_stage_velocity(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> StageVelocityResponse:
    """Retrieve average days spent between lifecycle stage transitions."""
    service = AnalyticsService(db)
    return await service.get_stage_velocity(current_user.id)


@router.get(
    "/timeline",
    response_model=TimelineAnalyticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get application submission volume over time",
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
    },
)
async def get_timeline_analytics(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> TimelineAnalyticsResponse:
    """Retrieve application submission counts bucketed chronologically."""
    service = AnalyticsService(db)
    return await service.get_timeline_analytics(current_user.id)
