from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ApplicationStage, ApplicationStatus
from app.core.security import create_access_token, hash_password
from app.models.application import Application
from app.models.company import Company
from app.models.user import User


@pytest.mark.asyncio
async def test_analytics_endpoints_api(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    company = Company(name="Palantir", user_id=test_user.id)
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)

    app = Application(
        user_id=test_user.id,
        company_id=company.id,
        job_title="Forward Deployed Software Engineer",
        current_stage=ApplicationStage.INTERVIEW,
        status=ApplicationStatus.ACTIVE,
        applied_date=date.today(),
    )
    db_session.add(app)
    await db_session.commit()
    await db_session.refresh(app)

    # 1. Dashboard
    dash_resp = await client.get("/api/v1/analytics/dashboard", headers=auth_headers)
    assert dash_resp.status_code == 200
    dash_data = dash_resp.json()
    assert dash_data["total_applications"] == 1
    assert dash_data["active_applications"] == 1
    assert dash_data["total_companies"] == 1

    # 2. Funnel
    funnel_resp = await client.get("/api/v1/analytics/funnel", headers=auth_headers)
    assert funnel_resp.status_code == 200
    funnel_data = funnel_resp.json()
    assert funnel_data["total_applications"] == 1
    assert len(funnel_data["stages"]) > 0

    # 3. Breakdown
    breakdown_resp = await client.get("/api/v1/analytics/breakdown", headers=auth_headers)
    assert breakdown_resp.status_code == 200
    breakdown_data = breakdown_resp.json()
    assert len(breakdown_data["by_stage"]) == 1
    assert breakdown_data["by_stage"][0]["name"] == "INTERVIEW"

    # 4. Velocity
    velocity_resp = await client.get("/api/v1/analytics/velocity", headers=auth_headers)
    assert velocity_resp.status_code == 200
    assert "transitions" in velocity_resp.json()

    # 5. Timeline
    timeline_resp = await client.get("/api/v1/analytics/timeline", headers=auth_headers)
    assert timeline_resp.status_code == 200
    timeline_data = timeline_resp.json()
    assert timeline_data["interval"] == "month"
    assert len(timeline_data["timeline"]) == 1


@pytest.mark.asyncio
async def test_analytics_tenant_isolation_api(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    # User 1 creates company and application
    company = Company(name="Snowflake", user_id=test_user.id)
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)

    app = Application(
        user_id=test_user.id,
        company_id=company.id,
        job_title="Data Platform Engineer",
        current_stage=ApplicationStage.OFFER,
        status=ApplicationStatus.ACTIVE,
        applied_date=date.today(),
    )
    db_session.add(app)
    await db_session.commit()

    # User 2 logs in
    other_user = User(
        email="other_analytics_user@example.com",
        password_hash=hash_password("OtherPassword123!"),
        full_name="Other Analytics User",
    )
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)
    other_headers = {"Authorization": f"Bearer {create_access_token(other_user.id)}"}

    # User 1 has 1 application and 1 offer
    u1_dash = await client.get("/api/v1/analytics/dashboard", headers=auth_headers)
    assert u1_dash.status_code == 200
    assert u1_dash.json()["total_applications"] == 1
    assert u1_dash.json()["offers_received"] == 1

    # User 2 has 0 applications and 0 offers
    u2_dash = await client.get("/api/v1/analytics/dashboard", headers=other_headers)
    assert u2_dash.status_code == 200
    assert u2_dash.json()["total_applications"] == 0
    assert u2_dash.json()["offers_received"] == 0
