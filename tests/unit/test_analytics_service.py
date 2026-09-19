from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    ApplicationSource,
    ApplicationStage,
    ApplicationStatus,
    InterviewStatus,
    InterviewType,
    LocationType,
    Priority,
)
from app.models.application import Application
from app.models.company import Company
from app.models.interview import Interview
from app.models.stage_history import ApplicationStageHistory
from app.models.user import User
from app.services.analytics_service import AnalyticsService


@pytest.mark.asyncio
async def test_dashboard_summary_kpis(db_session: AsyncSession, test_user: User) -> None:
    service = AnalyticsService(db_session)

    # Empty user state
    empty_summary = await service.get_dashboard_summary(test_user.id)
    assert empty_summary.total_applications == 0
    assert empty_summary.active_applications == 0
    assert empty_summary.response_rate == 0.0

    company = Company(name="Tesla", user_id=test_user.id)
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)

    # App 1: Applied -> Interview
    app1 = Application(
        user_id=test_user.id,
        company_id=company.id,
        job_title="Embedded Engineer",
        current_stage=ApplicationStage.INTERVIEW,
        status=ApplicationStatus.ACTIVE,
        applied_date=date.today() - timedelta(days=10),
    )
    # App 2: Offer
    app2 = Application(
        user_id=test_user.id,
        company_id=company.id,
        job_title="Firmware Engineer",
        current_stage=ApplicationStage.OFFER,
        status=ApplicationStatus.ACTIVE,
        applied_date=date.today() - timedelta(days=5),
    )
    # App 3: Saved (inactive)
    app3 = Application(
        user_id=test_user.id,
        company_id=company.id,
        job_title="Autopilot QA",
        current_stage=ApplicationStage.SAVED,
        status=ApplicationStatus.ARCHIVED,
        applied_date=date.today(),
    )
    db_session.add_all([app1, app2, app3])
    await db_session.commit()

    interview = Interview(
        application_id=app1.id,
        user_id=test_user.id,
        round_number=1,
        interview_type=InterviewType.TECHNICAL,
        title="CAN bus protocol",
        scheduled_at=datetime.now(UTC),
        status=InterviewStatus.SCHEDULED,
    )
    db_session.add(interview)
    await db_session.commit()

    summary = await service.get_dashboard_summary(test_user.id)
    assert summary.total_applications == 3
    assert summary.active_applications == 2
    assert summary.total_companies == 1
    assert summary.interviews_scheduled == 1
    assert summary.offers_received == 1
    assert summary.rejections_received == 0
    # Applied apps: app1 and app2 = 2. Both moved to interview/offer (2/2 = 100%)
    assert summary.response_rate == 100.0
    assert summary.offer_rate == 50.0


@pytest.mark.asyncio
async def test_funnel_and_breakdown_analytics(db_session: AsyncSession, test_user: User) -> None:
    company = Company(name="Amazon", user_id=test_user.id)
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)

    app = Application(
        user_id=test_user.id,
        company_id=company.id,
        job_title="SDE II",
        current_stage=ApplicationStage.SCREENING,
        source=ApplicationSource.LINKEDIN,
        location_type=LocationType.REMOTE,
        priority=Priority.HIGH,
    )
    db_session.add(app)
    await db_session.commit()

    service = AnalyticsService(db_session)

    funnel = await service.get_funnel_analytics(test_user.id)
    assert funnel.total_applications == 1
    screening_stage = next(s for s in funnel.stages if s.stage == "SCREENING")
    assert screening_stage.count == 1
    assert screening_stage.percentage_of_total == 100.0

    breakdown = await service.get_breakdown_analytics(test_user.id)
    assert len(breakdown.by_stage) == 1
    assert breakdown.by_stage[0].name == "SCREENING"
    assert breakdown.by_source[0].name == "LINKEDIN"
    assert breakdown.by_location_type[0].name == "REMOTE"
    assert breakdown.by_priority[0].name == "HIGH"


@pytest.mark.asyncio
async def test_stage_velocity_and_timeline(db_session: AsyncSession, test_user: User) -> None:
    company = Company(name="Twilio", user_id=test_user.id)
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)

    app = Application(
        user_id=test_user.id,
        company_id=company.id,
        job_title="Backend Engineer",
        current_stage=ApplicationStage.INTERVIEW,
        applied_date=date(2026, 8, 15),
    )
    db_session.add(app)
    await db_session.commit()
    await db_session.refresh(app)

    # Add transitions
    t1 = ApplicationStageHistory(
        application_id=app.id,
        from_stage=ApplicationStage.APPLIED,
        to_stage=ApplicationStage.SCREENING,
        changed_at=datetime(2026, 8, 16, tzinfo=UTC),
    )
    t2 = ApplicationStageHistory(
        application_id=app.id,
        from_stage=ApplicationStage.SCREENING,
        to_stage=ApplicationStage.INTERVIEW,
        changed_at=datetime(2026, 8, 20, tzinfo=UTC),
    )
    db_session.add_all([t1, t2])
    await db_session.commit()

    service = AnalyticsService(db_session)
    velocity = await service.get_stage_velocity(test_user.id)
    assert len(velocity.transitions) >= 1

    timeline = await service.get_timeline_analytics(test_user.id)
    assert len(timeline.timeline) == 1
    assert timeline.timeline[0].period == "2026-08"
    assert timeline.timeline[0].count == 1
