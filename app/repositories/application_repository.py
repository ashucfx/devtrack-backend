import uuid
from collections.abc import Sequence
from datetime import date
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.application import Application
from app.models.company import Company
from app.repositories.base import BaseRepository


class ApplicationRepository(BaseRepository[Application]):
    """Repository handling database operations for Application entity with database-level filtering."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Application, session)

    async def get_by_id_and_user(
        self, application_id: uuid.UUID, user_id: uuid.UUID
    ) -> Application | None:
        """Fetch a single application ensuring user ownership with company joined."""
        stmt = (
            select(Application)
            .options(selectinload(Application.company))
            .where(
                Application.id == application_id,
                Application.user_id == user_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    def _build_filter_conditions(
        self,
        user_id: uuid.UUID,
        status: str | None = None,
        stage: str | None = None,
        company_id: uuid.UUID | None = None,
        priority: str | None = None,
        employment_type: str | None = None,
        location_type: str | None = None,
        search: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[Any]:
        """Construct list of SQLAlchemy binary filter expressions."""
        conditions: list[Any] = [Application.user_id == user_id]

        if status:
            conditions.append(Application.status == status)
        if stage:
            conditions.append(Application.current_stage == stage)
        if company_id:
            conditions.append(Application.company_id == company_id)
        if priority:
            conditions.append(Application.priority == priority)
        if employment_type:
            conditions.append(Application.employment_type == employment_type)
        if location_type:
            conditions.append(Application.location_type == location_type)
        if date_from:
            conditions.append(Application.applied_date >= date_from)
        if date_to:
            conditions.append(Application.applied_date <= date_to)

        if search and search.strip():
            pattern = f"%{search.strip()}%"
            conditions.append(
                or_(
                    Application.job_title.ilike(pattern),
                    Application.location.ilike(pattern),
                    Company.name.ilike(pattern),
                )
            )

        return conditions

    async def list_by_user(
        self,
        user_id: uuid.UUID,
        status: str | None = None,
        stage: str | None = None,
        company_id: uuid.UUID | None = None,
        priority: str | None = None,
        employment_type: str | None = None,
        location_type: str | None = None,
        search: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        sort_by: str = "applied_date",
        sort_order: str = "desc",
        offset: int = 0,
        limit: int = 20,
    ) -> Sequence[Application]:
        """Query applications with database-level multi-column filtering, sorting, and pagination."""
        stmt = (
            select(Application)
            .join(Company, Application.company_id == Company.id)
            .options(selectinload(Application.company))
        )

        conditions = self._build_filter_conditions(
            user_id=user_id,
            status=status,
            stage=stage,
            company_id=company_id,
            priority=priority,
            employment_type=employment_type,
            location_type=location_type,
            search=search,
            date_from=date_from,
            date_to=date_to,
        )
        for cond in conditions:
            stmt = stmt.where(cond)

        # Sorting column mapping
        sort_column_map: dict[str, Any] = {
            "applied_date": Application.applied_date,
            "created_at": Application.created_at,
            "job_title": Application.job_title,
            "priority": Application.priority,
            "salary_max": Application.salary_max,
            "company_name": Company.name,
        }
        sort_col = sort_column_map.get(sort_by, Application.applied_date)

        if sort_order.lower() == "asc":
            stmt = stmt.order_by(sort_col.asc(), Application.id.asc())
        else:
            stmt = stmt.order_by(sort_col.desc(), Application.id.desc())

        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_by_user(
        self,
        user_id: uuid.UUID,
        status: str | None = None,
        stage: str | None = None,
        company_id: uuid.UUID | None = None,
        priority: str | None = None,
        employment_type: str | None = None,
        location_type: str | None = None,
        search: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> int:
        """Count total applications matching dynamic query conditions."""
        stmt = select(func.count(Application.id)).join(
            Company, Application.company_id == Company.id
        )

        conditions = self._build_filter_conditions(
            user_id=user_id,
            status=status,
            stage=stage,
            company_id=company_id,
            priority=priority,
            employment_type=employment_type,
            location_type=location_type,
            search=search,
            date_from=date_from,
            date_to=date_to,
        )
        for cond in conditions:
            stmt = stmt.where(cond)

        result = await self.session.execute(stmt)
        return result.scalar_one() or 0
