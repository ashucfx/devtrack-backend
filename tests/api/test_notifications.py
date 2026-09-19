import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import NotificationType
from app.core.security import create_access_token, hash_password
from app.models.notification import Notification
from app.models.user import User


@pytest.mark.asyncio
async def test_notifications_api_lifecycle(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    n1 = Notification(
        user_id=test_user.id,
        notification_type=NotificationType.STAGE_UPDATED,
        title="Application Advanced",
        message="Your application moved to Interview stage.",
        is_read=False,
    )
    n2 = Notification(
        user_id=test_user.id,
        notification_type=NotificationType.INTERVIEW_REMINDER,
        title="Interview Reminder",
        message="Interview starts tomorrow.",
        is_read=False,
    )
    db_session.add_all([n1, n2])
    await db_session.commit()

    # List notifications
    list_resp = await client.get("/api/v1/notifications", headers=auth_headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 2

    # Mark n1 as read
    read_resp = await client.patch(
        f"/api/v1/notifications/{n1.id}/read",
        headers=auth_headers,
    )
    assert read_resp.status_code == 200
    assert read_resp.json()["is_read"] is True

    # Filter unread only
    unread_resp = await client.get("/api/v1/notifications?unread_only=true", headers=auth_headers)
    assert unread_resp.status_code == 200
    unread_list = unread_resp.json()
    assert len(unread_list) == 1
    assert unread_list[0]["id"] == str(n2.id)

    # Mark all as read
    read_all_resp = await client.post("/api/v1/notifications/read-all", headers=auth_headers)
    assert read_all_resp.status_code == 200
    assert "Marked 1 notifications as read." in read_all_resp.json()["message"]


@pytest.mark.asyncio
async def test_notifications_tenant_isolation_api(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
) -> None:
    other_user = User(
        email="other_notif_user@example.com",
        password_hash=hash_password("OtherPassword123!"),
        full_name="Other Notif User",
    )
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)
    other_headers = {"Authorization": f"Bearer {create_access_token(other_user.id)}"}

    notification = Notification(
        user_id=test_user.id,
        notification_type=NotificationType.FOLLOW_UP_DUE,
        title="Secret Reminder",
        message="Confidential action required.",
        is_read=False,
    )
    db_session.add(notification)
    await db_session.commit()

    # Other tenant sees empty list
    other_list = await client.get("/api/v1/notifications", headers=other_headers)
    assert other_list.status_code == 200
    assert len(other_list.json()) == 0

    # Other tenant cannot mark test_user's notification as read
    other_patch = await client.patch(
        f"/api/v1/notifications/{notification.id}/read",
        headers=other_headers,
    )
    assert other_patch.status_code == 404
