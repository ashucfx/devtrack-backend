import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.company import Company
from app.models.user import User


@pytest.mark.asyncio
async def test_initial_creation_generates_stage_history_and_timeline(
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    company = Company(user_id=test_user.id, name="Oracle")
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)

    # 1. Create application
    create_resp = await client.post(
        "/api/v1/applications",
        json={
            "company_id": str(company.id),
            "job_title": "Database Kernel Developer",
            "current_stage": "SAVED",
        },
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    app_id = create_resp.json()["id"]

    # 2. Check timeline has initial entry
    timeline_resp = await client.get(
        f"/api/v1/applications/{app_id}/timeline", headers=auth_headers
    )
    assert timeline_resp.status_code == 200
    t_data = timeline_resp.json()
    assert t_data["application_id"] == app_id
    assert t_data["current_stage"] == "SAVED"
    assert len(t_data["timeline"]) == 1
    assert t_data["timeline"][0]["from_stage"] is None
    assert t_data["timeline"][0]["to_stage"] == "SAVED"


@pytest.mark.asyncio
async def test_stage_transition_progression(
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    company = Company(user_id=test_user.id, name="Cloudflare")
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)

    create_resp = await client.post(
        "/api/v1/applications",
        json={"company_id": str(company.id), "job_title": "Network Systems Engineer"},
        headers=auth_headers,
    )
    app_id = create_resp.json()["id"]
    assert create_resp.json()["current_stage"] == "APPLIED"

    # Transition 1: APPLIED -> SCREENING
    t1_resp = await client.post(
        f"/api/v1/applications/{app_id}/stage",
        json={"to_stage": "SCREENING", "notes": "Recruiter phone call scheduled"},
        headers=auth_headers,
    )
    assert t1_resp.status_code == 200
    assert t1_resp.json()["current_stage"] == "SCREENING"

    # Transition 2: SCREENING -> INTERVIEW
    t2_resp = await client.post(
        f"/api/v1/applications/{app_id}/stage",
        json={"to_stage": "INTERVIEW", "notes": "Round 1 Coding scheduled"},
        headers=auth_headers,
    )
    assert t2_resp.status_code == 200
    assert t2_resp.json()["current_stage"] == "INTERVIEW"

    # Transition 3: INTERVIEW -> OFFER
    t3_resp = await client.post(
        f"/api/v1/applications/{app_id}/stage",
        json={"to_stage": "OFFER", "notes": "Received formal offer letter"},
        headers=auth_headers,
    )
    assert t3_resp.status_code == 200
    assert t3_resp.json()["current_stage"] == "OFFER"

    # Verify timeline contains 4 entries in exact chronological order
    timeline_resp = await client.get(
        f"/api/v1/applications/{app_id}/timeline", headers=auth_headers
    )
    assert timeline_resp.status_code == 200
    history = timeline_resp.json()["timeline"]
    assert len(history) == 4
    assert history[0]["to_stage"] == "APPLIED"
    assert history[1]["to_stage"] == "SCREENING"
    assert history[2]["to_stage"] == "INTERVIEW"
    assert history[3]["to_stage"] == "OFFER"
    assert history[3]["notes"] == "Received formal offer letter"


@pytest.mark.asyncio
async def test_invalid_stage_transition_rejected(
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    company = Company(user_id=test_user.id, name="Adobe")
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)

    create_resp = await client.post(
        "/api/v1/applications",
        json={
            "company_id": str(company.id),
            "job_title": "Frontend Engineer",
            "current_stage": "SAVED",
        },
        headers=auth_headers,
    )
    app_id = create_resp.json()["id"]

    # Illegal transition: SAVED directly to OFFER
    bad_resp = await client.post(
        f"/api/v1/applications/{app_id}/stage",
        json={"to_stage": "OFFER"},
        headers=auth_headers,
    )
    assert bad_resp.status_code == 422
    assert bad_resp.json()["error"] == "INVALID_STATE_TRANSITION"


@pytest.mark.asyncio
async def test_cross_user_isolation_stage_and_timeline(
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    company = Company(user_id=test_user.id, name="User A Company")
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)

    create_resp = await client.post(
        "/api/v1/applications",
        json={"company_id": str(company.id), "job_title": "Engineer"},
        headers=auth_headers,
    )
    app_id = create_resp.json()["id"]

    # User B
    user_b = User(
        email="user_b_stage@example.com",
        password_hash=hash_password("Pass1234!"),
        full_name="User B",
    )
    db_session.add(user_b)
    await db_session.commit()
    await db_session.refresh(user_b)

    token_b = create_access_token(subject=user_b.id)
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User B cannot transition User A's application stage
    trans_resp = await client.post(
        f"/api/v1/applications/{app_id}/stage",
        json={"to_stage": "INTERVIEW"},
        headers=headers_b,
    )
    assert trans_resp.status_code == 404

    # User B cannot read User A's application timeline
    timeline_resp = await client.get(f"/api/v1/applications/{app_id}/timeline", headers=headers_b)
    assert timeline_resp.status_code == 404
