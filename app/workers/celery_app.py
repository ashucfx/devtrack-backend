from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "devtrack_workers",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,
    beat_schedule={
        "check-overdue-follow-ups-every-morning": {
            "task": "app.workers.tasks.check_overdue_follow_ups",
            "schedule": crontab(hour=8, minute=0),
        },
        "check-upcoming-interviews-hourly": {
            "task": "app.workers.tasks.check_upcoming_interviews",
            "schedule": crontab(minute=0),
        },
    },
)
