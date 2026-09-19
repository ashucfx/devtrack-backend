import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ApplicationStage
from app.models.application import Application
from app.models.company import Company
from app.models.user import User


@pytest.mark.asyncio
async def test_unauthenticated_request_handling(client: AsyncClient) -> None:
    endpoints = [
        ("GET", "/api/v1/users/me"),
        ("GET", "/api/v1/companies"),
        ("GET", "/api/v1/applications"),
        ("GET", "/api/v1/follow-ups"),
        ("GET", "/api/v1/analytics/dashboard"),
        ("GET", "/api/v1/notifications"),
    ]

    for method, path in endpoints:
        if method == "GET":
            resp = await client.get(path)
        elif method == "POST":
            resp = await client.post(path)
        assert resp.status_code == 401
        err_json = resp.json()
        assert "detail" in err_json or "message" in err_json


@pytest.mark.asyncio
async def test_duplicate_company_name_conflict(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    # First create
    resp1 = await client.post(
        "/api/v1/companies",
        headers=auth_headers,
        json={"name": "Duplicate Inc"},
    )
    assert resp1.status_code == 201

    # Second create with same name
    resp2 = await client.post(
        "/api/v1/companies",
        headers=auth_headers,
        json={"name": "Duplicate Inc"},
    )
    assert resp2.status_code == 409
    err = resp2.json()
    assert err["status_code"] == 409
    assert "already exists" in err["message"]


@pytest.mark.asyncio
async def test_invalid_fsm_stage_transition_error(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    company = Company(name="FinTech Corp", user_id=test_user.id)
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)

    app = Application(
        user_id=test_user.id,
        company_id=company.id,
        job_title="Software Architect",
        current_stage=ApplicationStage.SAVED,
    )
    db_session.add(app)
    await db_session.commit()
    await db_session.refresh(app)

    # Illegal transition: SAVED directly to OFFER
    resp = await client.post(
        f"/api/v1/applications/{app.id}/stage",
        headers=auth_headers,
        json={"to_stage": "OFFER"},
    )
    assert resp.status_code == 422
    err = resp.json()
    assert err["status_code"] == 422
    assert "Cannot transition application from 'SAVED' to 'OFFER'" in err["message"]


@pytest.mark.asyncio
async def test_validation_errors_format(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    # Empty company name
    resp = await client.post(
        "/api/v1/companies",
        headers=auth_headers,
        json={"name": ""},
    )
    assert resp.status_code == 422
    err = resp.json()
    assert err["status_code"] == 422
    assert "details" in err
