import uuid
from collections import defaultdict

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ApplicationStage
from app.core.redis import redis_manager
from app.repositories.analytics_repository import AnalyticsRepository
from app.schemas.analytics import (
    BreakdownAnalyticsResponse,
    DashboardSummaryResponse,
    DistributionMetric,
    FunnelAnalyticsResponse,
    FunnelStageMetric,
    StageVelocityMetric,
    StageVelocityResponse,
    TimelineAnalyticsResponse,
    TimelineMetric,
)


class AnalyticsService:
    """Service providing aggregated business intelligence and recruiting insights."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.analytics_repo = AnalyticsRepository(session)

    async def get_dashboard_summary(self, user_id: uuid.UUID) -> DashboardSummaryResponse:
        """Fetch high-level KPI dashboard metrics with Redis cache-aside."""
        cache_key = redis_manager.dashboard_cache_key(user_id)
        cached = await redis_manager.get_json(cache_key)
        if cached:
            return DashboardSummaryResponse(**cached)

        kpis = await self.analytics_repo.get_dashboard_kpis(user_id)
        response = DashboardSummaryResponse(**kpis)
        await redis_manager.set_json(cache_key, response.model_dump(), ttl_seconds=300)
        return response

    @staticmethod
    async def invalidate_dashboard_cache(user_id: uuid.UUID) -> None:
        """Invalidate cached dashboard KPIs for a tenant."""
        cache_key = redis_manager.dashboard_cache_key(user_id)
        await redis_manager.delete(cache_key)

    async def get_funnel_analytics(self, user_id: uuid.UUID) -> FunnelAnalyticsResponse:
        """Calculate funnel progression and stage-by-stage conversion drop-off."""
        stage_counts = await self.analytics_repo.get_funnel_counts(user_id)
        total_apps = sum(stage_counts.values())

        funnel_order = [
            ApplicationStage.SAVED,
            ApplicationStage.APPLIED,
            ApplicationStage.SCREENING,
            ApplicationStage.ONLINE_ASSESSMENT,
            ApplicationStage.INTERVIEW,
            ApplicationStage.OFFER,
            ApplicationStage.REJECTED,
            ApplicationStage.WITHDRAWN,
        ]

        stages: list[FunnelStageMetric] = []
        prev_count: int | None = None

        for stg in funnel_order:
            count = stage_counts.get(stg, 0)
            percentage = round((count / total_apps * 100), 2) if total_apps > 0 else 0.0

            conversion = None
            if prev_count is not None:
                conversion = round((count / prev_count * 100), 2) if prev_count > 0 else 0.0

            stages.append(
                FunnelStageMetric(
                    stage=stg,
                    count=count,
                    percentage_of_total=percentage,
                    conversion_from_previous=conversion,
                )
            )
            prev_count = count

        return FunnelAnalyticsResponse(
            total_applications=total_apps,
            stages=stages,
        )

    async def get_breakdown_analytics(self, user_id: uuid.UUID) -> BreakdownAnalyticsResponse:
        """Compute multidimensional categorical distribution of user applications."""

        async def _calc_dist(attr: str) -> list[DistributionMetric]:
            tuples = await self.analytics_repo.get_breakdown_by_attribute(user_id, attr)
            total = sum(t[1] for t in tuples)
            return [
                DistributionMetric(
                    name=t[0],
                    count=t[1],
                    percentage=round((t[1] / total * 100), 2) if total > 0 else 0.0,
                )
                for t in tuples
            ]

        by_stage = await _calc_dist("current_stage")
        by_source = await _calc_dist("source")
        by_loc = await _calc_dist("location_type")
        by_priority = await _calc_dist("priority")

        return BreakdownAnalyticsResponse(
            by_stage=by_stage,
            by_source=by_source,
            by_location_type=by_loc,
            by_priority=by_priority,
        )

    async def get_stage_velocity(self, user_id: uuid.UUID) -> StageVelocityResponse:
        """Compute average time duration between stage transitions."""
        transitions = await self.analytics_repo.get_stage_transitions(user_id)

        durations_by_pair: dict[tuple[str, str], list[float]] = defaultdict(list)
        app_last_change: dict[uuid.UUID, float] = {}

        for tr in transitions:
            key = (tr.from_stage or "UNKNOWN", tr.to_stage)
            cur_time = tr.changed_at.timestamp()
            if tr.application_id in app_last_change:
                elapsed_days = (cur_time - app_last_change[tr.application_id]) / 86400.0
                durations_by_pair[key].append(max(0.0, elapsed_days))
            else:
                durations_by_pair[key].append(0.0)
            app_last_change[tr.application_id] = cur_time

        results: list[StageVelocityMetric] = []
        for (from_s, to_s), dur_list in durations_by_pair.items():
            avg_dur = round(sum(dur_list) / len(dur_list), 2) if dur_list else 0.0
            results.append(
                StageVelocityMetric(
                    from_stage=from_s,
                    to_stage=to_s,
                    transition_count=len(dur_list),
                    avg_duration_days=avg_dur,
                )
            )

        results.sort(key=lambda x: x.transition_count, reverse=True)
        return StageVelocityResponse(transitions=results)

    async def get_timeline_analytics(self, user_id: uuid.UUID) -> TimelineAnalyticsResponse:
        """Fetch historical application volume trends."""
        data = await self.analytics_repo.get_timeline_series(user_id)
        metrics = [TimelineMetric(period=item[0], count=item[1]) for item in data]
        return TimelineAnalyticsResponse(
            interval="month",
            timeline=metrics,
        )
