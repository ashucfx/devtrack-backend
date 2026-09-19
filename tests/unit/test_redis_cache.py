import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ApplicationStage, ApplicationStatus
from app.core.redis import redis_manager
from app.models.application import Application
from app.models.company import Company
from app.models.user import User
from app.services.analytics_service import AnalyticsService


@pytest.mark.asyncio
async def test_redis_manager_json_operations() -> None:
    test_key = "devtrack:test:key"
    payload = {"name": "DevTrack", "version": "1.0.0", "active": True}

    # Set
    success = await redis_manager.set_json(test_key, payload, ttl_seconds=60)
    assert success is True

    # Get
    retrieved = await redis_manager.get_json(test_key)
    assert retrieved == payload

    # Delete
    deleted = await redis_manager.delete(test_key)
    assert deleted is True

    # Get after delete
    assert await redis_manager.get_json(test_key) is None


@pytest.mark.asyncio
async def test_dashboard_cache_aside_and_invalidation(
    db_session: AsyncSession, test_user: User
) -> None:

    company = Company(name="HuggingFace", user_id=test_user.id)
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)

    app = Application(
        user_id=test_user.id,
        company_id=company.id,
        job_title="ML Infra Engineer",
        current_stage=ApplicationStage.APPLIED,
        status=ApplicationStatus.ACTIVE,
    )
    db_session.add(app)
    await db_session.commit()

    service = AnalyticsService(db_session)
    cache_key = redis_manager.dashboard_cache_key(test_user.id)

    # Initially cache should be empty
    assert await redis_manager.get_json(cache_key) is None

    # First call: populates cache
    summary1 = await service.get_dashboard_summary(test_user.id)
    assert summary1.total_applications == 1

    # Cache should now contain the serialized data
    cached_data = await redis_manager.get_json(cache_key)
    assert cached_data is not None
    assert cached_data["total_applications"] == 1

    # Second call: served directly from cache
    summary2 = await service.get_dashboard_summary(test_user.id)
    assert summary2.total_applications == 1

    # Invalidate
    await AnalyticsService.invalidate_dashboard_cache(test_user.id)
    assert await redis_manager.get_json(cache_key) is None
