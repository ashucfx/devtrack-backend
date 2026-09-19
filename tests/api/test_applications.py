from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.company import Company
from app.models.user import User


@pytest.mark.asyncio
async def test_create_and_get_application(
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    # Create company first
    company = Company(user_id=test_user.id, name="Github", location="San Francisco, CA")
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)

    payload = {
        "company_id": str(company.id),
        "job_title": "Senior Platform Engineer",
        "job_url": "https://github.com/careers/456",
        "employment_type": "FULL_TIME",
        "location": "Remote - US",
        "location_type": "REMOTE",
        "salary_min": 175000,
        "salary_max": 225000,
        "currency": "USD",
        "source": "LINKEDIN",
        "applied_date": str(date.today()),
        "current_stage": "APPLIED",
        "status": "ACTIVE",
        "priority": "HIGH",
        "notes": "Applied via LinkedIn Easy Apply",
    }
    response = await client.post("/api/v1/applications", json=payload, headers=auth_headers)
    assert response.status_code == 201

    data = response.json()
    assert data["job_title"] == "Senior Platform Engineer"
    assert data["company"]["name"] == "Github"
    app_id = data["id"]

    # Get by ID
    get_resp = await client.get(f"/api/v1/applications/{app_id}", headers=auth_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == app_id


@pytest.mark.asyncio
async def test_create_application_with_other_user_company_forbidden(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    # Company owned by another user
    other_user = User(
        email="other_owner@example.com",
        password_hash=hash_password("Pass1234!"),
        full_name="Other Owner",
    )
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)

    other_company = Company(user_id=other_user.id, name="OtherCorp")
    db_session.add(other_company)
    await db_session.commit()
    await db_session.refresh(other_company)

    payload = {
        "company_id": str(other_company.id),
        "job_title": "Security Engineer",
    }
    response = await client.post("/api/v1/applications", json=payload, headers=auth_headers)
    assert response.status_code == 404
    assert response.json()["error"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_filter_and_search_applications(
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    # Seed 2 companies
    c1 = Company(user_id=test_user.id, name="Spotify", location="New York")
    c2 = Company(user_id=test_user.id, name="Discord", location="San Francisco")
    db_session.add_all([c1, c2])
    await db_session.commit()
    await db_session.refresh(c1)
    await db_session.refresh(c2)

    today = date.today()
    yesterday = today - timedelta(days=1)

    # Seed 3 applications
    await client.post(
        "/api/v1/applications",
        json={
            "company_id": str(c1.id),
            "job_title": "Backend Python Architect",
            "current_stage": "INTERVIEW",
            "priority": "URGENT",
            "applied_date": str(today),
            "location": "New York",
        },
        headers=auth_headers,
    )
    await client.post(
        "/api/v1/applications",
        json={
            "company_id": str(c2.id),
            "job_title": "Infrastructure Engineer",
            "current_stage": "APPLIED",
            "priority": "MEDIUM",
            "applied_date": str(yesterday),
            "location": "San Francisco",
        },
        headers=auth_headers,
    )
    await client.post(
        "/api/v1/applications",
        json={
            "company_id": str(c1.id),
            "job_title": "Data Platform Lead",
            "current_stage": "OFFER",
            "priority": "HIGH",
            "applied_date": str(today),
            "location": "Remote",
        },
        headers=auth_headers,
    )

    # 1. Filter by stage = INTERVIEW
    resp_stage = await client.get("/api/v1/applications?stage=INTERVIEW", headers=auth_headers)
    assert resp_stage.status_code == 200
    assert resp_stage.json()["total"] == 1
    assert resp_stage.json()["items"][0]["job_title"] == "Backend Python Architect"

    # 2. Filter by priority = HIGH
    resp_priority = await client.get("/api/v1/applications?priority=HIGH", headers=auth_headers)
    assert resp_priority.status_code == 200
    assert resp_priority.json()["total"] == 1
    assert resp_priority.json()["items"][0]["job_title"] == "Data Platform Lead"

    # 3. Search query matching company name 'spotify'
    resp_search_company = await client.get(
        "/api/v1/applications?search=spotify", headers=auth_headers
    )
    assert resp_search_company.status_code == 200
    assert resp_search_company.json()["total"] == 2

    # 4. Filter by date range (only today)
    resp_date = await client.get(
        f"/api/v1/applications?date_from={today}&date_to={today}",
        headers=auth_headers,
    )
    assert resp_date.status_code == 200
    assert resp_date.json()["total"] == 2


@pytest.mark.asyncio
async def test_update_and_delete_application_api(
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    company = Company(user_id=test_user.id, name="Figma")
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)

    create_resp = await client.post(
        "/api/v1/applications",
        json={"company_id": str(company.id), "job_title": "Fullstack Engineer"},
        headers=auth_headers,
    )
    app_id = create_resp.json()["id"]

    # Patch job title
    patch_resp = await client.patch(
        f"/api/v1/applications/{app_id}",
        json={"job_title": "Senior Fullstack Engineer", "priority": "HIGH"},
        headers=auth_headers,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["job_title"] == "Senior Fullstack Engineer"
    assert patch_resp.json()["priority"] == "HIGH"

    # Delete
    del_resp = await client.delete(f"/api/v1/applications/{app_id}", headers=auth_headers)
    assert del_resp.status_code == 204

    # 404 after delete
    get_resp = await client.get(f"/api/v1/applications/{app_id}", headers=auth_headers)
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_cross_user_isolation_application(
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    # User A creates company and application
    company_a = Company(user_id=test_user.id, name="User A Employer")
    db_session.add(company_a)
    await db_session.commit()
    await db_session.refresh(company_a)

    create_resp = await client.post(
        "/api/v1/applications",
        json={"company_id": str(company_a.id), "job_title": "Secret Project Engineer"},
        headers=auth_headers,
    )
    app_id = create_resp.json()["id"]

    # User B
    user_b = User(
        email="applicant_b@example.com",
        password_hash=hash_password("Pass1234!"),
        full_name="Applicant B",
    )
    db_session.add(user_b)
    await db_session.commit()
    await db_session.refresh(user_b)

    token_b = create_access_token(subject=user_b.id)
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User B cannot read User A application
    get_resp = await client.get(f"/api/v1/applications/{app_id}", headers=headers_b)
    assert get_resp.status_code == 404

    # User B cannot modify User A application
    patch_resp = await client.patch(
        f"/api/v1/applications/{app_id}",
        json={"job_title": "Hijacked Role"},
        headers=headers_b,
    )
    assert patch_resp.status_code == 404

    # User B cannot delete User A application
    del_resp = await client.delete(f"/api/v1/applications/{app_id}", headers=headers_b)
    assert del_resp.status_code == 404
