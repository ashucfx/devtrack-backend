from datetime import date, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import FollowUpStatus
from app.core.exceptions import EntityNotFoundException
from app.models.application import Application
from app.models.company import Company
from app.models.user import User
from app.schemas.follow_up import FollowUpCreate, FollowUpUpdate
from app.services.follow_up_service import FollowUpService


@pytest.mark.asyncio
async def test_create_and_get_follow_up(db_session: AsyncSession, test_user: User) -> None:
    company = Company(name="Microsoft", user_id=test_user.id)
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)

    app = Application(
        user_id=test_user.id,
        company_id=company.id,
        job_title="Principal Engineer",
    )
    db_session.add(app)
    await db_session.commit()
    await db_session.refresh(app)

    service = FollowUpService(db_session)
    due = date.today() + timedelta(days=3)
    created = await service.create_follow_up(
        app.id,
        test_user.id,
        FollowUpCreate(
            title="Send thank you note to hiring manager",
            due_date=due,
            notes="Emphasize Azure infrastructure experience",
        ),
    )

    assert created.id is not None
    assert created.title == "Send thank you note to hiring manager"
    assert created.due_date == due
    assert created.status == FollowUpStatus.PENDING
    assert created.application_id == app.id
    assert created.user_id == test_user.id

    fetched = await service.get_follow_up(created.id, test_user.id)
    assert fetched.id == created.id


@pytest.mark.asyncio
async def test_follow_up_timeframe_filters(db_session: AsyncSession, test_user: User) -> None:
    company = Company(name="Oracle", user_id=test_user.id)
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)

    app = Application(
        user_id=test_user.id,
        company_id=company.id,
        job_title="Cloud Engineer",
    )
    db_session.add(app)
    await db_session.commit()
    await db_session.refresh(app)

    service = FollowUpService(db_session)
    today = date.today()

    # Overdue task
    await service.create_follow_up(
        app.id,
        test_user.id,
        FollowUpCreate(
            title="Overdue task",
            due_date=today - timedelta(days=2),
        ),
    )

    # Today task
    await service.create_follow_up(
        app.id,
        test_user.id,
        FollowUpCreate(
            title="Today task",
            due_date=today,
        ),
    )

    # Upcoming task
    await service.create_follow_up(
        app.id,
        test_user.id,
        FollowUpCreate(
            title="Upcoming task",
            due_date=today + timedelta(days=5),
        ),
    )

    today_items = await service.list_follow_ups(test_user.id, timeframe="today")
    assert len(today_items) == 1
    assert today_items[0].title == "Today task"

    overdue_items = await service.list_follow_ups(test_user.id, timeframe="overdue")
    assert len(overdue_items) == 1
    assert overdue_items[0].title == "Overdue task"

    upcoming_items = await service.list_follow_ups(test_user.id, timeframe="upcoming")
    # Both today and +5 days qualify for upcoming (due_date >= today)
    assert len(upcoming_items) == 2


@pytest.mark.asyncio
async def test_update_and_delete_follow_up(db_session: AsyncSession, test_user: User) -> None:
    company = Company(name="Airbnb", user_id=test_user.id)
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)

    app = Application(
        user_id=test_user.id,
        company_id=company.id,
        job_title="Fullstack Developer",
    )
    db_session.add(app)
    await db_session.commit()
    await db_session.refresh(app)

    service = FollowUpService(db_session)
    follow_up = await service.create_follow_up(
        app.id,
        test_user.id,
        FollowUpCreate(
            title="Follow up on interview feedback",
            due_date=date.today() + timedelta(days=7),
        ),
    )

    # Mark completed
    updated = await service.update_follow_up(
        follow_up.id,
        test_user.id,
        FollowUpUpdate(status=FollowUpStatus.COMPLETED),
    )
    assert updated.status == FollowUpStatus.COMPLETED

    # Delete
    await service.delete_follow_up(follow_up.id, test_user.id)

    with pytest.raises(EntityNotFoundException):
        await service.get_follow_up(follow_up.id, test_user.id)
