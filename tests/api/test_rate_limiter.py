import pytest
from httpx import AsyncClient

from app.core.config import get_settings
from app.models.user import User

settings = get_settings()


@pytest.mark.asyncio
async def test_login_rate_limiting_api(
    client: AsyncClient,
    test_user: User,
) -> None:
    # Max login requests is configured as RATE_LIMIT_LOGIN_MAX_REQUESTS (default 5)
    max_reqs = settings.RATE_LIMIT_LOGIN_MAX_REQUESTS

    for i in range(max_reqs):
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": test_user.email, "password": "WrongPassword!"},
        )
        # 401 Unauthorized for wrong password
        assert resp.status_code == 401, f"Attempt {i + 1} failed with status {resp.status_code}"

    # Next attempt should trigger 429 Too Many Requests
    rate_limited_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": "WrongPassword!"},
    )
    assert rate_limited_resp.status_code == 429
    err_json = rate_limited_resp.json()
    assert "Rate limit exceeded" in err_json["message"]
