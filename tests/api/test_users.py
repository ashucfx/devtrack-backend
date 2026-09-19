import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import User


@pytest.mark.asyncio
async def test_get_my_profile_authenticated(
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    response = await client.get("/api/v1/users/me", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == str(test_user.id)
    assert data["email"] == test_user.email
    assert data["full_name"] == test_user.full_name
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_get_my_profile_unauthenticated(client: AsyncClient) -> None:
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_my_profile_name(
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    payload = {"full_name": "Updated Dev Name"}
    response = await client.patch("/api/v1/users/me", json=payload, headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["full_name"] == "Updated Dev Name"
    assert data["email"] == test_user.email


@pytest.mark.asyncio
async def test_update_my_profile_duplicate_email(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    # Create another user
    other_user = User(
        email="other@example.com",
        password_hash=hash_password("Pass123456!"),
        full_name="Other User",
        is_active=True,
    )
    db_session.add(other_user)
    await db_session.commit()

    # Attempt to change email to other_user email
    payload = {"email": "other@example.com"}
    response = await client.patch("/api/v1/users/me", json=payload, headers=auth_headers)
    assert response.status_code == 409
    data = response.json()
    assert data["error"] == "CONFLICT"
