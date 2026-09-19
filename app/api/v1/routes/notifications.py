import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_active_user
from app.api.dependencies.database import get_db
from app.models.user import User
from app.schemas.common import ErrorResponse, MessageResponse
from app.schemas.notification import NotificationRead
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get(
    "",
    response_model=list[NotificationRead],
    status_code=status.HTTP_200_OK,
    summary="List user notifications",
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
    },
)
async def list_notifications(
    unread_only: bool = Query(default=False, description="Filter for unread notifications only"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[NotificationRead]:
    """Retrieve notification alerts and reminders for the authenticated user."""
    service = NotificationService(db)
    notifications = await service.list_notifications(current_user.id, unread_only=unread_only)
    return [NotificationRead.model_validate(n) for n in notifications]


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationRead,
    status_code=status.HTTP_200_OK,
    summary="Mark a notification as read",
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Notification not found"},
    },
)
async def mark_notification_as_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationRead:
    """Mark a specific notification item as read."""
    service = NotificationService(db)
    notification = await service.mark_as_read(notification_id, current_user.id)
    return NotificationRead.model_validate(notification)


@router.post(
    "/read-all",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark all unread notifications as read",
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
    },
)
async def mark_all_notifications_as_read(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Mark all unread inbox items as read."""
    service = NotificationService(db)
    count = await service.mark_all_as_read(current_user.id)
    return MessageResponse(message=f"Marked {count} notifications as read.")
