import uuid
from collections import defaultdict
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ApplicationStage, ApplicationStatus, InterviewStatus
from app.models.application import Application
from app.models.company import Company
from app.models.interview import Interview
from app.models.stage_history import ApplicationStageHistory


class AnalyticsRepository:
    """Repository executing optimized SQL aggregation queries for analytics."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_dashboard_kpis(self, user_id: uuid.UUID) -> dict:
        """Compute key summary KPIs for the user dashboard in parallel/direct aggregations."""
        # 1. Application counts by stage and status
        app_stmt = (
            select(
                Application.status,
                Application.current_stage,
                func.count().label("cnt"),
            )
            .where(Application.user_id == user_id)
            .group_by(Application.status, Application.current_stage)
        )
        app_result = await self.session.execute(app_stmt)
        app_rows = app_result.all()

        total_applications = sum(row.cnt for row in app_rows)
        active_applications = sum(
            row.cnt for row in app_rows if row.status == ApplicationStatus.ACTIVE
        )
        offers_received = sum(
            row.cnt for row in app_rows if row.current_stage == ApplicationStage.OFFER
        )
        rejections_received = sum(
            row.cnt for row in app_rows if row.current_stage == ApplicationStage.REJECTED
        )

        # 2. Total companies
        comp_stmt = select(func.count()).select_from(Company).where(Company.user_id == user_id)
        comp_result = await self.session.execute(comp_stmt)
        total_companies = comp_result.scalar_one()

        # 3. Scheduled interviews
        interview_stmt = (
            select(func.count())
            .select_from(Interview)
            .where(
                Interview.user_id == user_id,
                Interview.status == InterviewStatus.SCHEDULED,
            )
        )
        interview_result = await self.session.execute(interview_stmt)
        interviews_scheduled = interview_result.scalar_one()

        # 4. Response rate: applications that moved beyond SAVED and APPLIED (or were rejected/offered)
        applied_total = sum(
            row.cnt for row in app_rows if row.current_stage != ApplicationStage.SAVED
        )
        responded_total = sum(
            row.cnt
            for row in app_rows
            if row.current_stage not in (ApplicationStage.SAVED, ApplicationStage.APPLIED)
        )

        response_rate = (
            round((responded_total / applied_total) * 100, 2) if applied_total > 0 else 0.0
        )
        offer_rate = round((offers_received / applied_total) * 100, 2) if applied_total > 0 else 0.0

        return {
            "total_applications": total_applications,
            "active_applications": active_applications,
            "total_companies": total_companies,
            "interviews_scheduled": interviews_scheduled,
            "offers_received": offers_received,
            "rejections_received": rejections_received,
            "response_rate": min(100.0, max(0.0, response_rate)),
            "offer_rate": min(100.0, max(0.0, offer_rate)),
        }

    async def get_funnel_counts(self, user_id: uuid.UUID) -> dict[str, int]:
        """Aggregate application counts across stages."""
        stmt = (
            select(Application.current_stage, func.count().label("cnt"))
            .where(Application.user_id == user_id)
            .group_by(Application.current_stage)
        )
        result = await self.session.execute(stmt)
        return {row.current_stage: row.cnt for row in result.all()}

    async def get_breakdown_by_attribute(
        self, user_id: uuid.UUID, attribute_name: str
    ) -> Sequence[tuple[str, int]]:
        """Compute distribution counts for a specified application column."""
        col = getattr(Application, attribute_name)
        stmt = (
            select(col, func.count().label("cnt"))
            .where(Application.user_id == user_id)
            .group_by(col)
            .order_by(func.count().desc())
        )
        result = await self.session.execute(stmt)
        return [(str(row[0]), row[1]) for row in result.all()]

    async def get_stage_transitions(self, user_id: uuid.UUID) -> Sequence[ApplicationStageHistory]:
        """Retrieve stage history logs belonging to user applications for velocity analysis."""
        stmt = (
            select(ApplicationStageHistory)
            .join(Application, Application.id == ApplicationStageHistory.application_id)
            .where(
                Application.user_id == user_id,
                ApplicationStageHistory.from_stage.isnot(None),
            )
            .order_by(
                ApplicationStageHistory.application_id,
                ApplicationStageHistory.changed_at.asc(),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_timeline_series(self, user_id: uuid.UUID) -> Sequence[tuple[str, int]]:
        """Retrieve application volume grouped by calendar month."""
        stmt = select(Application.applied_date).where(Application.user_id == user_id)
        result = await self.session.execute(stmt)
        dates = result.scalars().all()

        counts: dict[str, int] = defaultdict(int)
        for d in dates:
            month_key = d.strftime("%Y-%m")
            counts[month_key] += 1

        sorted_items = sorted(counts.items(), key=lambda x: x[0])
        return sorted_items
