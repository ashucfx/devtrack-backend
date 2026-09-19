import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EntityNotFoundException
from app.models.notification import Notification
from app.repositories.notification_repository import NotificationRepository
from app.schemas.notification import NotificationCreate


class NotificationService:
    """Service handling user notification inbox and background alert dispatches."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.notification_repo = NotificationRepository(session)

    async def create_notification(
        self, user_id: uuid.UUID, notification_in: NotificationCreate
    ) -> Notification:
        """Create and dispatch a new notification to user inbox."""
        notification = Notification(
            user_id=user_id,
            notification_type=notification_in.notification_type,
            title=notification_in.title.strip(),
            message=notification_in.message.strip(),
            is_read=False,
        )
        notification = await self.notification_repo.create(notification)
        await self.session.commit()
        return notification

    async def list_notifications(
        self,
        user_id: uuid.UUID,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Notification]:
        """List notifications for the user."""
        return await self.notification_repo.list_by_user(
            user_id=user_id,
            unread_only=unread_only,
            limit=limit,
            offset=offset,
        )

    async def mark_as_read(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> Notification:
        """Mark a single notification as read enforcing tenant isolation."""
        notification = await self.notification_repo.get_by_id_and_user(notification_id, user_id)
        if not notification:
            raise EntityNotFoundException("Notification", notification_id)

        if not notification.is_read:
            notification.is_read = True
            await self.session.commit()
        return notification

    async def mark_all_as_read(self, user_id: uuid.UUID) -> int:
        """Mark all unread notifications as read."""
        count = await self.notification_repo.mark_all_as_read(user_id)
        await self.session.commit()
        return count
