import asyncio
import logging
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import FollowUpStatus, InterviewStatus, NotificationType
from app.db.session import AsyncSessionLocal
from app.models.follow_up import FollowUp
from app.models.interview import Interview
from app.models.notification import Notification
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


async def process_overdue_follow_ups(session: AsyncSession) -> int:
    """Scan and generate notification alerts for overdue or due-today follow-ups."""
    today = date.today()
    stmt = select(FollowUp).where(
        FollowUp.due_date <= today,
        FollowUp.status == FollowUpStatus.PENDING,
    )
    result = await session.execute(stmt)
    follow_ups = result.scalars().all()

    created_count = 0
    for fu in follow_ups:
        # Check if notification for today already exists to prevent duplicate alerts
        existing_stmt = select(Notification).where(
            Notification.user_id == fu.user_id,
            Notification.notification_type == NotificationType.FOLLOW_UP_DUE,
            Notification.title.like(f"%{fu.title}%"),
        )
        existing_res = await session.execute(existing_stmt)
        if not existing_res.first():
            notification = Notification(
                user_id=fu.user_id,
                notification_type=NotificationType.FOLLOW_UP_DUE,
                title=f"Follow-up Due: {fu.title}",
                message=f"Your scheduled follow-up '{fu.title}' was due on {fu.due_date}.",
                is_read=False,
            )
            session.add(notification)
            created_count += 1

    if created_count > 0:
        await session.commit()
    return created_count


async def process_upcoming_interviews(session: AsyncSession) -> int:
    """Scan and generate reminder alerts for interviews scheduled in next 24 hours."""
    now = datetime.now(UTC)
    next_24h = now + timedelta(hours=24)

    stmt = select(Interview).where(
        Interview.scheduled_at >= now,
        Interview.scheduled_at <= next_24h,
        Interview.status == InterviewStatus.SCHEDULED,
    )
    result = await session.execute(stmt)
    interviews = result.scalars().all()

    created_count = 0
    for it in interviews:
        existing_stmt = select(Notification).where(
            Notification.user_id == it.user_id,
            Notification.notification_type == NotificationType.INTERVIEW_REMINDER,
            Notification.title.like(f"%{it.title}%"),
        )
        existing_res = await session.execute(existing_stmt)
        if not existing_res.first():
            notification = Notification(
                user_id=it.user_id,
                notification_type=NotificationType.INTERVIEW_REMINDER,
                title=f"Interview Reminder: {it.title}",
                message=(
                    f"You have Round {it.round_number} ({it.interview_type}) scheduled at "
                    f"{it.scheduled_at.strftime('%Y-%m-%d %H:%M UTC')}."
                ),
                is_read=False,
            )
            session.add(notification)
            created_count += 1

    if created_count > 0:
        await session.commit()
    return created_count


@celery_app.task(name="app.workers.tasks.check_overdue_follow_ups")
def check_overdue_follow_ups() -> dict[str, int]:
    """Celery periodic task for overdue follow-up alerts."""

    async def _run() -> int:
        async with AsyncSessionLocal() as session:
            return await process_overdue_follow_ups(session)

    count = asyncio.run(_run())
    logger.info("Generated %d overdue follow-up notifications", count)
    return {"created_notifications": count}


@celery_app.task(name="app.workers.tasks.check_upcoming_interviews")
def check_upcoming_interviews() -> dict[str, int]:
    """Celery periodic task for upcoming interview reminder alerts."""

    async def _run() -> int:
        async with AsyncSessionLocal() as session:
            return await process_upcoming_interviews(session)

    count = asyncio.run(_run())
    logger.info("Generated %d upcoming interview reminder notifications", count)
    return {"created_notifications": count}
