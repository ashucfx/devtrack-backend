import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EntityNotFoundException
from app.models.follow_up import FollowUp
from app.repositories.application_repository import ApplicationRepository
from app.repositories.follow_up_repository import FollowUpRepository
from app.schemas.follow_up import FollowUpCreate, FollowUpUpdate


class FollowUpService:
    """Service handling scheduled follow-ups, state toggles, and tenant boundaries."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.follow_up_repo = FollowUpRepository(session)
        self.application_repo = ApplicationRepository(session)

    async def create_follow_up(
        self, application_id: uuid.UUID, user_id: uuid.UUID, follow_up_in: FollowUpCreate
    ) -> FollowUp:
        """Create a follow-up reminder after verifying application tenant ownership."""
        application = await self.application_repo.get_by_id_and_user(application_id, user_id)
        if not application:
            raise EntityNotFoundException("Application", application_id)

        follow_up = FollowUp(
            application_id=application_id,
            user_id=user_id,
            title=follow_up_in.title.strip(),
            due_date=follow_up_in.due_date,
            status=follow_up_in.status,
            notes=follow_up_in.notes.strip() if follow_up_in.notes else None,
        )
        follow_up = await self.follow_up_repo.create(follow_up)
        await self.session.commit()
        return follow_up

    async def get_follow_up(self, follow_up_id: uuid.UUID, user_id: uuid.UUID) -> FollowUp:
        """Retrieve a specific follow-up task enforcing user isolation."""
        follow_up = await self.follow_up_repo.get_by_id_and_user(follow_up_id, user_id)
        if not follow_up:
            raise EntityNotFoundException("FollowUp", follow_up_id)
        return follow_up

    async def list_follow_ups_for_application(
        self, application_id: uuid.UUID, user_id: uuid.UUID
    ) -> Sequence[FollowUp]:
        """List all follow-up tasks for an application after verifying tenant ownership."""
        application = await self.application_repo.get_by_id_and_user(application_id, user_id)
        if not application:
            raise EntityNotFoundException("Application", application_id)
        return await self.follow_up_repo.list_by_application(application_id, user_id)

    async def list_follow_ups(
        self,
        user_id: uuid.UUID,
        status: str | None = None,
        timeframe: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[FollowUp]:
        """List all follow-up tasks for the user with optional status and timeframe filters."""
        return await self.follow_up_repo.list_by_user(
            user_id=user_id,
            status=status,
            timeframe=timeframe,
            limit=limit,
            offset=offset,
        )

    async def update_follow_up(
        self,
        follow_up_id: uuid.UUID,
        user_id: uuid.UUID,
        follow_up_update: FollowUpUpdate,
    ) -> FollowUp:
        """Update follow-up details or completion status."""
        follow_up = await self.get_follow_up(follow_up_id, user_id)
        update_dict = follow_up_update.model_dump(exclude_unset=True)

        for str_field in ["title", "notes"]:
            if str_field in update_dict and isinstance(update_dict[str_field], str):
                update_dict[str_field] = update_dict[str_field].strip()

        if update_dict:
            follow_up = await self.follow_up_repo.update(follow_up, **update_dict)
            await self.session.commit()

        return follow_up

    async def delete_follow_up(self, follow_up_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """Delete a follow-up task enforcing user isolation."""
        follow_up = await self.get_follow_up(follow_up_id, user_id)
        await self.follow_up_repo.delete(follow_up)
        await self.session.commit()
