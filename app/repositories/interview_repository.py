import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interview import Interview
from app.repositories.base import BaseRepository


class InterviewRepository(BaseRepository[Interview]):
    """Repository handling database operations for Interview rounds."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Interview, session)

    async def get_by_id_and_user(
        self, interview_id: uuid.UUID, user_id: uuid.UUID
    ) -> Interview | None:
        """Fetch an interview by ID enforcing user isolation."""
        stmt = select(Interview).where(
            Interview.id == interview_id,
            Interview.user_id == user_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_application(
        self, application_id: uuid.UUID, user_id: uuid.UUID
    ) -> Sequence[Interview]:
        """Fetch all interviews for an application ordered by round number."""
        stmt = (
            select(Interview)
            .where(
                Interview.application_id == application_id,
                Interview.user_id == user_id,
            )
            .order_by(Interview.round_number.asc(), Interview.scheduled_at.asc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_by_user(
        self,
        user_id: uuid.UUID,
        status: str | None = None,
        upcoming_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[Interview]:
        """Fetch all interviews for a user with optional status and upcoming filters."""
        stmt = select(Interview).where(Interview.user_id == user_id)
        if status:
            stmt = stmt.where(Interview.status == status)
        if upcoming_only:
            now = datetime.now(UTC)
            stmt = stmt.where(Interview.scheduled_at >= now)
        stmt = stmt.order_by(Interview.scheduled_at.asc()).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_next_round_number(self, application_id: uuid.UUID) -> int:
        """Calculate the next sequential round number for an application."""
        stmt = select(func.coalesce(func.max(Interview.round_number), 0)).where(
            Interview.application_id == application_id
        )
        result = await self.session.execute(stmt)
        max_round = result.scalar_one()
        return max_round + 1
