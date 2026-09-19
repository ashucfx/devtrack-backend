import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ApplicationSource, ApplicationStage, ApplicationStatus, Priority
from app.core.exceptions import EntityNotFoundException
from app.models.company import Company
from app.models.user import User
from app.schemas.application import ApplicationCreate, ApplicationUpdate
from app.services.application_service import ApplicationService


@pytest.mark.asyncio
async def test_create_application_success(db_session: AsyncSession, test_user: User) -> None:
    # Seed company
    company = Company(user_id=test_user.id, name="Tesla", location="Austin, TX")
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)

    service = ApplicationService(db_session)
    app_in = ApplicationCreate(
        company_id=company.id,
        job_title="Senior Python Backend Engineer",
        job_url="https://tesla.com/careers/123",
        salary_min=Decimal("160000"),
        salary_max=Decimal("200000"),
        currency="USD",
        source=ApplicationSource.REFERRAL,
        applied_date=date.today(),
        current_stage=ApplicationStage.APPLIED,
        status=ApplicationStatus.ACTIVE,
        priority=Priority.HIGH,
        notes="Referred by senior infra engineer",
    )
    application = await service.create_application(app_in, test_user.id)
    assert application.id is not None
    assert application.job_title == "Senior Python Backend Engineer"
    assert application.company.name == "Tesla"
    assert application.user_id == test_user.id


@pytest.mark.asyncio
async def test_create_application_invalid_or_foreign_company(
    db_session: AsyncSession, test_user: User
) -> None:
    service = ApplicationService(db_session)
    app_in = ApplicationCreate(
        company_id=uuid.uuid4(),
        job_title="Software Engineer",
    )

    with pytest.raises(EntityNotFoundException):
        await service.create_application(app_in, test_user.id)


@pytest.mark.asyncio
async def test_update_and_delete_application(db_session: AsyncSession, test_user: User) -> None:
    company = Company(user_id=test_user.id, name="OpenAI")
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)

    service = ApplicationService(db_session)
    app_in = ApplicationCreate(company_id=company.id, job_title="Backend Engineer")
    application = await service.create_application(app_in, test_user.id)

    updated = await service.update_application(
        application.id,
        ApplicationUpdate(job_title="Staff Backend Engineer", priority=Priority.URGENT),
        test_user.id,
    )
    assert updated.job_title == "Staff Backend Engineer"
    assert updated.priority == Priority.URGENT

    await service.delete_application(application.id, test_user.id)
    with pytest.raises(EntityNotFoundException):
        await service.get_application(application.id, test_user.id)
