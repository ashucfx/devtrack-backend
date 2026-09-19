import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import InterviewStatus, InterviewType
from app.core.exceptions import EntityNotFoundException
from app.models.application import Application
from app.models.company import Company
from app.models.user import User
from app.schemas.interview import InterviewCreate, InterviewUpdate
from app.services.interview_service import InterviewService


@pytest.mark.asyncio
async def test_create_and_get_interview(db_session: AsyncSession, test_user: User) -> None:
    company = Company(name="Acme Corp", user_id=test_user.id)
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)

    app = Application(
        user_id=test_user.id,
        company_id=company.id,
        job_title="Senior Backend Engineer",
    )
    db_session.add(app)
    await db_session.commit()
    await db_session.refresh(app)

    service = InterviewService(db_session)
    interview_in = InterviewCreate(
        round_number=1,
        interview_type=InterviewType.TECHNICAL,
        title="Coding & Data Structures",
        scheduled_at=datetime.now(UTC),
        duration_minutes=60,
        meeting_url="https://meet.google.com/abc-def-ghi",
        interviewer_names="Jane Doe, John Smith",
        status=InterviewStatus.SCHEDULED,
        notes="Prepare graph algorithms",
    )

    created = await service.create_interview(app.id, test_user.id, interview_in)
    assert created.id is not None
    assert created.round_number == 1
    assert created.title == "Coding & Data Structures"
    assert created.application_id == app.id
    assert created.user_id == test_user.id

    fetched = await service.get_interview(created.id, test_user.id)
    assert fetched.id == created.id
    assert fetched.round_number == 1


@pytest.mark.asyncio
async def test_interview_tenant_isolation(db_session: AsyncSession, test_user: User) -> None:
    other_user_id = uuid.uuid4()
    service = InterviewService(db_session)

    interview_in = InterviewCreate(
        round_number=1,
        interview_type=InterviewType.HR,
        title="Screening Call",
        scheduled_at=datetime.now(UTC),
    )

    # Creating interview for non-existent or other user's application
    with pytest.raises(EntityNotFoundException):
        await service.create_interview(uuid.uuid4(), test_user.id, interview_in)

    # Other user cannot access test_user's interview
    company = Company(name="Stripe", user_id=test_user.id)
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)

    app = Application(
        user_id=test_user.id,
        company_id=company.id,
        job_title="Staff Engineer",
    )
    db_session.add(app)
    await db_session.commit()
    await db_session.refresh(app)

    interview = await service.create_interview(app.id, test_user.id, interview_in)

    with pytest.raises(EntityNotFoundException):
        await service.get_interview(interview.id, other_user_id)


@pytest.mark.asyncio
async def test_update_and_delete_interview(db_session: AsyncSession, test_user: User) -> None:
    company = Company(name="Netflix", user_id=test_user.id)
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)

    app = Application(
        user_id=test_user.id,
        company_id=company.id,
        job_title="Software Engineer",
    )
    db_session.add(app)
    await db_session.commit()
    await db_session.refresh(app)

    service = InterviewService(db_session)
    interview = await service.create_interview(
        app.id,
        test_user.id,
        InterviewCreate(
            round_number=1,
            interview_type=InterviewType.SYSTEM_DESIGN,
            title="System Design Architecture",
            scheduled_at=datetime.now(UTC),
        ),
    )

    # Update status and feedback
    updated = await service.update_interview(
        interview.id,
        test_user.id,
        InterviewUpdate(
            status=InterviewStatus.COMPLETED,
            feedback="Strong distributed systems knowledge, clear communication.",
        ),
    )
    assert updated.status == InterviewStatus.COMPLETED
    assert "Strong distributed systems" in (updated.feedback or "")

    # Delete
    await service.delete_interview(interview.id, test_user.id)

    with pytest.raises(EntityNotFoundException):
        await service.get_interview(interview.id, test_user.id)
