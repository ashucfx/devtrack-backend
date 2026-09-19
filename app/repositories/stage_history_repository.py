import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stage_history import ApplicationStageHistory
from app.repositories.base import BaseRepository


class StageHistoryRepository(BaseRepository[ApplicationStageHistory]):
    """Repository handling append-only stage history logs."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(ApplicationStageHistory, session)

    async def record_transition(
        self,
        application_id: uuid.UUID,
        from_stage: str | None,
        to_stage: str,
        notes: str | None = None,
    ) -> ApplicationStageHistory:
        """Append an immutable stage transition audit entry."""
        entry = ApplicationStageHistory(
            application_id=application_id,
            from_stage=from_stage,
            to_stage=to_stage,
            notes=notes.strip() if notes else None,
        )
        return await self.create(entry)

    async def get_timeline(self, application_id: uuid.UUID) -> Sequence[ApplicationStageHistory]:
        """Retrieve the complete chronological progression of an application."""
        stmt = (
            select(ApplicationStageHistory)
            .where(ApplicationStageHistory.application_id == application_id)
            .order_by(ApplicationStageHistory.changed_at.asc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
