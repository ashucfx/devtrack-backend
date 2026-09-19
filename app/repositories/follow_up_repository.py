import uuid
from collections.abc import Sequence
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import FollowUpStatus
from app.models.follow_up import FollowUp
from app.repositories.base import BaseRepository


class FollowUpRepository(BaseRepository[FollowUp]):
    """Repository handling database operations for FollowUp tasks."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(FollowUp, session)

    async def get_by_id_and_user(
        self, follow_up_id: uuid.UUID, user_id: uuid.UUID
    ) -> FollowUp | None:
        """Fetch a follow-up task by ID enforcing tenant isolation."""
        stmt = select(FollowUp).where(
            FollowUp.id == follow_up_id,
            FollowUp.user_id == user_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_application(
        self, application_id: uuid.UUID, user_id: uuid.UUID
    ) -> Sequence[FollowUp]:
        """Fetch all follow-ups for a specific application ordered chronologically."""
        stmt = (
            select(FollowUp)
            .where(
                FollowUp.application_id == application_id,
                FollowUp.user_id == user_id,
            )
            .order_by(FollowUp.due_date.asc(), FollowUp.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_by_user(
        self,
        user_id: uuid.UUID,
        status: str | None = None,
        timeframe: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[FollowUp]:
        """Fetch follow-up tasks for a user with timeframe and status filters."""
        stmt = select(FollowUp).where(FollowUp.user_id == user_id)
        today = date.today()

        if status:
            stmt = stmt.where(FollowUp.status == status)

        if timeframe:
            match timeframe.lower():
                case "today":
                    stmt = stmt.where(FollowUp.due_date == today)
                case "overdue":
                    stmt = stmt.where(
                        FollowUp.due_date < today,
                        FollowUp.status == FollowUpStatus.PENDING,
                    )
                case "upcoming":
                    stmt = stmt.where(
                        FollowUp.due_date >= today,
                        FollowUp.status == FollowUpStatus.PENDING,
                    )

        stmt = stmt.order_by(FollowUp.due_date.asc(), FollowUp.created_at.asc())
        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_by_user(
        self,
        user_id: uuid.UUID,
        status: str | None = None,
        timeframe: str | None = None,
    ) -> int:
        """Count follow-up tasks matching criteria for user."""
        stmt = select(func.count()).select_from(FollowUp).where(FollowUp.user_id == user_id)
        today = date.today()

        if status:
            stmt = stmt.where(FollowUp.status == status)

        if timeframe:
            match timeframe.lower():
                case "today":
                    stmt = stmt.where(FollowUp.due_date == today)
                case "overdue":
                    stmt = stmt.where(
                        FollowUp.due_date < today,
                        FollowUp.status == FollowUpStatus.PENDING,
                    )
                case "upcoming":
                    stmt = stmt.where(
                        FollowUp.due_date >= today,
                        FollowUp.status == FollowUpStatus.PENDING,
                    )

        result = await self.session.execute(stmt)
        return result.scalar_one()
