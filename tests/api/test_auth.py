import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient, db_session: AsyncSession) -> None:
    payload = {
        "email": "developer@example.com",
        "full_name": "Dev User",
        "password": "SuperSecretPassword123!",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "developer@example.com"
    assert data["user"]["full_name"] == "Dev User"

    # Verify user exists in database
    result = await db_session.execute(select(User).where(User.email == "developer@example.com"))
    user = result.scalar_one_or_none()
    assert user is not None
    assert user.full_name == "Dev User"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, test_user: User) -> None:
    payload = {
        "email": test_user.email,
        "full_name": "Duplicate User",
        "password": "Password123!",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409

    data = response.json()
    assert data["error"] == "CONFLICT"


@pytest.mark.asyncio
async def test_register_short_password(client: AsyncClient) -> None:
    payload = {
        "email": "short@example.com",
        "full_name": "Short Pass User",
        "password": "123",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user: User) -> None:
    payload = {
        "email": test_user.email,
        "password": "TestPassword123!",
    }
    response = await client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["email"] == test_user.email


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, test_user: User) -> None:
    payload = {
        "email": test_user.email,
        "password": "IncorrectPassword!",
    }
    response = await client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 401

    data = response.json()
    assert data["error"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_login_nonexistent_email(client: AsyncClient) -> None:
    payload = {
        "email": "unknown@example.com",
        "password": "SomePassword123!",
    }
    response = await client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_rotation(client: AsyncClient, test_user: User) -> None:
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": "TestPassword123!"},
    )
    old_refresh_token = login_resp.json()["refresh_token"]

    # Refresh tokens
    refresh_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh_token},
    )
    assert refresh_resp.status_code == 200
    new_data = refresh_resp.json()
    assert "access_token" in new_data
    assert "refresh_token" in new_data
    assert new_data["refresh_token"] != old_refresh_token

    # Reusing the old refresh token must fail (Token Rotation security)
    replay_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh_token},
    )
    assert replay_resp.status_code == 401


@pytest.mark.asyncio
async def test_logout_revocation(client: AsyncClient, test_user: User) -> None:
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": "TestPassword123!"},
    )
    refresh_token = login_resp.json()["refresh_token"]

    # Logout
    logout_resp = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
    )
    assert logout_resp.status_code == 204

    # Verify refresh token is now revoked
    refresh_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_resp.status_code == 401
