from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    FollowUpStatus,
    InterviewStatus,
    InterviewType,
)
from app.models.application import Application
from app.models.company import Company
from app.models.follow_up import FollowUp
from app.models.interview import Interview
from app.models.user import User
from app.workers.tasks import process_overdue_follow_ups, process_upcoming_interviews


@pytest.mark.asyncio
async def test_process_overdue_follow_ups(db_session: AsyncSession, test_user: User) -> None:
    company = Company(name="Oracle Cloud", user_id=test_user.id)
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)

    app = Application(
        user_id=test_user.id,
        company_id=company.id,
        job_title="OCI Infrastructure Engineer",
    )
    db_session.add(app)
    await db_session.commit()
    await db_session.refresh(app)

    # Overdue follow up
    fu1 = FollowUp(
        application_id=app.id,
        user_id=test_user.id,
        title="Send portfolio repository",
        due_date=date.today() - timedelta(days=1),
        status=FollowUpStatus.PENDING,
    )
    # Completed follow up (should not trigger alert)
    fu2 = FollowUp(
        application_id=app.id,
        user_id=test_user.id,
        title="Completed task",
        due_date=date.today() - timedelta(days=1),
        status=FollowUpStatus.COMPLETED,
    )
    db_session.add_all([fu1, fu2])
    await db_session.commit()

    created_count = await process_overdue_follow_ups(db_session)
    assert created_count == 1

    # Running again should be idempotent (prevent duplicates)
    second_run_count = await process_overdue_follow_ups(db_session)
    assert second_run_count == 0


@pytest.mark.asyncio
async def test_process_upcoming_interviews(db_session: AsyncSession, test_user: User) -> None:
    company = Company(name="Cloudflare", user_id=test_user.id)
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)

    app = Application(
        user_id=test_user.id,
        company_id=company.id,
        job_title="Edge Network Engineer",
    )
    db_session.add(app)
    await db_session.commit()
    await db_session.refresh(app)

    # Interview in 4 hours
    it1 = Interview(
        application_id=app.id,
        user_id=test_user.id,
        round_number=1,
        interview_type=InterviewType.TECHNICAL,
        title="BGP & Anycast Deep Dive",
        scheduled_at=datetime.now(UTC) + timedelta(hours=4),
        status=InterviewStatus.SCHEDULED,
    )
    # Interview in 4 days (not in next 24h)
    it2 = Interview(
        application_id=app.id,
        user_id=test_user.id,
        round_number=2,
        interview_type=InterviewType.SYSTEM_DESIGN,
        title="Global CDN Architecture",
        scheduled_at=datetime.now(UTC) + timedelta(days=4),
        status=InterviewStatus.SCHEDULED,
    )
    db_session.add_all([it1, it2])
    await db_session.commit()

    created_count = await process_upcoming_interviews(db_session)
    assert created_count == 1

    # Idempotent second run
    second_run = await process_upcoming_interviews(db_session)
    assert second_run == 0
