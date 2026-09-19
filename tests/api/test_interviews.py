from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import InterviewType
from app.core.security import create_access_token, hash_password
from app.models.application import Application
from app.models.company import Company
from app.models.interview import Interview
from app.models.user import User


@pytest.mark.asyncio
async def test_create_and_list_interviews_api(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    company = Company(name="Google", user_id=test_user.id)
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)

    app = Application(
        user_id=test_user.id,
        company_id=company.id,
        job_title="Software Engineer III",
    )
    db_session.add(app)
    await db_session.commit()
    await db_session.refresh(app)

    scheduled_time = (datetime.now(UTC) + timedelta(days=2)).isoformat()

    # Schedule interview round 1
    create_resp = await client.post(
        f"/api/v1/applications/{app.id}/interviews",
        headers=auth_headers,
        json={
            "round_number": 1,
            "interview_type": "CODING",
            "title": "Algorithms & Data Structures",
            "scheduled_at": scheduled_time,
            "duration_minutes": 45,
            "meeting_url": "https://meet.google.com/xyz-abcd-efg",
            "interviewer_names": "Alex Staff Eng",
            "status": "SCHEDULED",
            "notes": "Review dynamic programming",
        },
    )
    assert create_resp.status_code == 201
    created_data = create_resp.json()
    assert created_data["round_number"] == 1
    assert created_data["title"] == "Algorithms & Data Structures"
    assert created_data["application_id"] == str(app.id)
    interview_id = created_data["id"]

    # Schedule interview round 2
    create_resp2 = await client.post(
        f"/api/v1/applications/{app.id}/interviews",
        headers=auth_headers,
        json={
            "round_number": 2,
            "interview_type": "SYSTEM_DESIGN",
            "title": "Distributed Systems Architecture",
            "scheduled_at": (datetime.now(UTC) + timedelta(days=5)).isoformat(),
            "duration_minutes": 60,
        },
    )
    assert create_resp2.status_code == 201

    # List interviews
    list_resp = await client.get(
        f"/api/v1/applications/{app.id}/interviews",
        headers=auth_headers,
    )
    assert list_resp.status_code == 200
    interviews_list = list_resp.json()
    assert len(interviews_list) == 2
    assert interviews_list[0]["round_number"] == 1
    assert interviews_list[1]["round_number"] == 2

    # Get single interview
    get_resp = await client.get(
        f"/api/v1/interviews/{interview_id}",
        headers=auth_headers,
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == interview_id


@pytest.mark.asyncio
async def test_update_and_delete_interview_api(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    company = Company(name="Meta", user_id=test_user.id)
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)

    app = Application(
        user_id=test_user.id,
        company_id=company.id,
        job_title="Production Engineer",
    )
    db_session.add(app)
    await db_session.commit()
    await db_session.refresh(app)

    interview = Interview(
        application_id=app.id,
        user_id=test_user.id,
        round_number=1,
        interview_type=InterviewType.TECHNICAL,
        title="Linux Systems Internals",
        scheduled_at=datetime.now(UTC) + timedelta(days=1),
    )
    db_session.add(interview)
    await db_session.commit()
    await db_session.refresh(interview)

    # Patch interview
    patch_resp = await client.patch(
        f"/api/v1/interviews/{interview.id}",
        headers=auth_headers,
        json={
            "status": "COMPLETED",
            "feedback": "Covered kernel namespaces, cgroups, and eBPF. Excellent performance.",
        },
    )
    assert patch_resp.status_code == 200
    patched_data = patch_resp.json()
    assert patched_data["status"] == "COMPLETED"
    assert "Covered kernel namespaces" in patched_data["feedback"]

    # Delete interview
    delete_resp = await client.delete(
        f"/api/v1/interviews/{interview.id}",
        headers=auth_headers,
    )
    assert delete_resp.status_code == 204

    # Verify 404 after deletion
    get_after_delete = await client.get(
        f"/api/v1/interviews/{interview.id}",
        headers=auth_headers,
    )
    assert get_after_delete.status_code == 404


@pytest.mark.asyncio
async def test_interview_tenant_isolation_api(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
) -> None:
    other_user = User(
        email="other_tenant@example.com",
        password_hash=hash_password("OtherPassword123!"),
        full_name="Other Tenant",
    )
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)
    other_headers = {"Authorization": f"Bearer {create_access_token(other_user.id)}"}

    company = Company(name="Amazon", user_id=test_user.id)
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)

    app = Application(
        user_id=test_user.id,
        company_id=company.id,
        job_title="Solutions Architect",
    )
    db_session.add(app)
    await db_session.commit()
    await db_session.refresh(app)

    interview = Interview(
        application_id=app.id,
        user_id=test_user.id,
        round_number=1,
        interview_type=InterviewType.MANAGERIAL,
        title="Leadership Principles",
        scheduled_at=datetime.now(UTC) + timedelta(days=3),
    )
    db_session.add(interview)
    await db_session.commit()
    await db_session.refresh(interview)

    # Other tenant cannot read test_user's interview list
    other_list_resp = await client.get(
        f"/api/v1/applications/{app.id}/interviews",
        headers=other_headers,
    )
    assert other_list_resp.status_code == 404

    # Other tenant cannot read test_user's interview by ID
    other_get_resp = await client.get(
        f"/api/v1/interviews/{interview.id}",
        headers=other_headers,
    )
    assert other_get_resp.status_code == 404

    # Other tenant cannot patch test_user's interview
    other_patch_resp = await client.patch(
        f"/api/v1/interviews/{interview.id}",
        headers=other_headers,
        json={"status": "CANCELLED"},
    )
    assert other_patch_resp.status_code == 404

    # Other tenant cannot delete test_user's interview
    other_delete_resp = await client.delete(
        f"/api/v1/interviews/{interview.id}",
        headers=other_headers,
    )
    assert other_delete_resp.status_code == 404
