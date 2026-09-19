import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import NotificationType
from app.core.exceptions import EntityNotFoundException
from app.models.user import User
from app.schemas.notification import NotificationCreate
from app.services.notification_service import NotificationService


@pytest.mark.asyncio
async def test_create_and_list_notifications(db_session: AsyncSession, test_user: User) -> None:
    service = NotificationService(db_session)

    n1 = await service.create_notification(
        test_user.id,
        NotificationCreate(
            notification_type=NotificationType.FOLLOW_UP_DUE,
            title="Follow-up Due: Thank you note",
            message="Your follow-up is due today.",
        ),
    )
    assert n1.id is not None
    assert n1.is_read is False

    n2 = await service.create_notification(
        test_user.id,
        NotificationCreate(
            notification_type=NotificationType.INTERVIEW_REMINDER,
            title="Interview in 2 hours",
            message="System Design with hiring manager.",
        ),
    )
    assert n2.id is not None

    all_notifications = await service.list_notifications(test_user.id)
    assert len(all_notifications) == 2

    # Mark single as read
    marked = await service.mark_as_read(n1.id, test_user.id)
    assert marked.is_read is True

    # Check unread only
    unread = await service.list_notifications(test_user.id, unread_only=True)
    assert len(unread) == 1
    assert unread[0].id == n2.id

    # Mark all as read
    count = await service.mark_all_as_read(test_user.id)
    assert count == 1

    unread_after = await service.list_notifications(test_user.id, unread_only=True)
    assert len(unread_after) == 0


@pytest.mark.asyncio
async def test_notification_tenant_isolation(db_session: AsyncSession, test_user: User) -> None:
    service = NotificationService(db_session)
    other_user_id = uuid.uuid4()

    n = await service.create_notification(
        test_user.id,
        NotificationCreate(
            title="Private Alert",
            message="Confidential interview feedback received.",
        ),
    )

    with pytest.raises(EntityNotFoundException):
        await service.mark_as_read(n.id, other_user_id)
