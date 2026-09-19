from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.application import Application
from app.models.company import Company
from app.models.follow_up import FollowUp
from app.models.user import User


@pytest.mark.asyncio
async def test_create_and_list_follow_ups_api(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    company = Company(name="Salesforce", user_id=test_user.id)
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)

    app = Application(
        user_id=test_user.id,
        company_id=company.id,
        job_title="Lead Software Engineer",
    )
    db_session.add(app)
    await db_session.commit()
    await db_session.refresh(app)

    today = date.today()

    # Create follow up
    create_resp = await client.post(
        f"/api/v1/applications/{app.id}/follow-ups",
        headers=auth_headers,
        json={
            "title": "Email recruiter about OA results",
            "due_date": today.isoformat(),
            "notes": "Ask about team match round timeline",
        },
    )
    assert create_resp.status_code == 201
    follow_up_data = create_resp.json()
    assert follow_up_data["title"] == "Email recruiter about OA results"
    assert follow_up_data["status"] == "PENDING"
    assert follow_up_data["application_id"] == str(app.id)
    follow_up_id = follow_up_data["id"]

    # List application follow ups
    app_list_resp = await client.get(
        f"/api/v1/applications/{app.id}/follow-ups",
        headers=auth_headers,
    )
    assert app_list_resp.status_code == 200
    assert len(app_list_resp.json()) == 1

    # Global list with timeframe=today
    global_list_resp = await client.get(
        "/api/v1/follow-ups?timeframe=today",
        headers=auth_headers,
    )
    assert global_list_resp.status_code == 200
    assert len(global_list_resp.json()) == 1
    assert global_list_resp.json()[0]["id"] == follow_up_id


@pytest.mark.asyncio
async def test_update_and_delete_follow_up_api(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    company = Company(name="Adobe", user_id=test_user.id)
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)

    app = Application(
        user_id=test_user.id,
        company_id=company.id,
        job_title="Senior Python Backend Developer",
    )
    db_session.add(app)
    await db_session.commit()
    await db_session.refresh(app)

    follow_up = FollowUp(
        application_id=app.id,
        user_id=test_user.id,
        title="Check status of portfolio review",
        due_date=date.today() + timedelta(days=2),
    )
    db_session.add(follow_up)
    await db_session.commit()
    await db_session.refresh(follow_up)

    # Patch status to COMPLETED
    patch_resp = await client.patch(
        f"/api/v1/follow-ups/{follow_up.id}",
        headers=auth_headers,
        json={"status": "COMPLETED"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "COMPLETED"

    # Delete follow up
    delete_resp = await client.delete(
        f"/api/v1/follow-ups/{follow_up.id}",
        headers=auth_headers,
    )
    assert delete_resp.status_code == 204

    # 404 on subsequent get
    get_after_delete = await client.get(
        f"/api/v1/follow-ups/{follow_up.id}",
        headers=auth_headers,
    )
    assert get_after_delete.status_code == 404


@pytest.mark.asyncio
async def test_follow_up_tenant_isolation_api(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
) -> None:
    other_user = User(
        email="other_follow_user@example.com",
        password_hash=hash_password("OtherPassword123!"),
        full_name="Other Follow User",
    )
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)
    other_headers = {"Authorization": f"Bearer {create_access_token(other_user.id)}"}

    company = Company(name="Snap", user_id=test_user.id)
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)

    app = Application(
        user_id=test_user.id,
        company_id=company.id,
        job_title="Core Backend Engineer",
    )
    db_session.add(app)
    await db_session.commit()
    await db_session.refresh(app)

    follow_up = FollowUp(
        application_id=app.id,
        user_id=test_user.id,
        title="Ping hiring manager",
        due_date=date.today(),
    )
    db_session.add(follow_up)
    await db_session.commit()
    await db_session.refresh(follow_up)

    # Other tenant cannot read test_user's follow-ups
    other_app_list = await client.get(
        f"/api/v1/applications/{app.id}/follow-ups",
        headers=other_headers,
    )
    assert other_app_list.status_code == 404

    # Other tenant global follow-ups is empty
    other_global = await client.get(
        "/api/v1/follow-ups",
        headers=other_headers,
    )
    assert other_global.status_code == 200
    assert len(other_global.json()) == 0

    # Other tenant cannot patch or delete
    other_patch = await client.patch(
        f"/api/v1/follow-ups/{follow_up.id}",
        headers=other_headers,
        json={"status": "COMPLETED"},
    )
    assert other_patch.status_code == 404

    other_del = await client.delete(
        f"/api/v1/follow-ups/{follow_up.id}",
        headers=other_headers,
    )
    assert other_del.status_code == 404
