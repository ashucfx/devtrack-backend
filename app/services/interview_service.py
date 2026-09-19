import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EntityNotFoundException
from app.models.interview import Interview
from app.repositories.application_repository import ApplicationRepository
from app.repositories.interview_repository import InterviewRepository
from app.schemas.interview import InterviewCreate, InterviewUpdate


class InterviewService:
    """Service handling interview lifecycle, validation, and multi-tenant scoping."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.interview_repo = InterviewRepository(session)
        self.application_repo = ApplicationRepository(session)

    async def create_interview(
        self, application_id: uuid.UUID, user_id: uuid.UUID, interview_in: InterviewCreate
    ) -> Interview:
        """Schedule an interview round after verifying application tenant ownership."""
        application = await self.application_repo.get_by_id_and_user(application_id, user_id)
        if not application:
            raise EntityNotFoundException("Application", application_id)

        interview = Interview(
            application_id=application_id,
            user_id=user_id,
            round_number=interview_in.round_number,
            interview_type=interview_in.interview_type,
            title=interview_in.title.strip(),
            scheduled_at=interview_in.scheduled_at,
            duration_minutes=interview_in.duration_minutes,
            meeting_url=interview_in.meeting_url.strip() if interview_in.meeting_url else None,
            interviewer_names=(
                interview_in.interviewer_names.strip() if interview_in.interviewer_names else None
            ),
            status=interview_in.status,
            feedback=interview_in.feedback.strip() if interview_in.feedback else None,
            notes=interview_in.notes.strip() if interview_in.notes else None,
        )
        interview = await self.interview_repo.create(interview)
        await self.session.commit()
        from app.services.analytics_service import AnalyticsService

        await AnalyticsService.invalidate_dashboard_cache(user_id)
        return interview

    async def get_interview(self, interview_id: uuid.UUID, user_id: uuid.UUID) -> Interview:
        """Retrieve a specific interview round enforcing tenant isolation."""
        interview = await self.interview_repo.get_by_id_and_user(interview_id, user_id)
        if not interview:
            raise EntityNotFoundException("Interview", interview_id)
        return interview

    async def list_interviews(
        self, application_id: uuid.UUID, user_id: uuid.UUID
    ) -> Sequence[Interview]:
        """List all interview rounds for an application after verifying tenant ownership."""
        application = await self.application_repo.get_by_id_and_user(application_id, user_id)
        if not application:
            raise EntityNotFoundException("Application", application_id)
        return await self.interview_repo.list_by_application(application_id, user_id)

    async def update_interview(
        self, interview_id: uuid.UUID, user_id: uuid.UUID, interview_update: InterviewUpdate
    ) -> Interview:
        """Update interview round details with tenant validation."""
        interview = await self.get_interview(interview_id, user_id)
        update_dict = interview_update.model_dump(exclude_unset=True)

        for str_field in ["title", "meeting_url", "interviewer_names", "feedback", "notes"]:
            if str_field in update_dict and isinstance(update_dict[str_field], str):
                update_dict[str_field] = update_dict[str_field].strip()

        if update_dict:
            interview = await self.interview_repo.update(interview, **update_dict)
            await self.session.commit()
            from app.services.analytics_service import AnalyticsService

            await AnalyticsService.invalidate_dashboard_cache(user_id)

        return interview

    async def delete_interview(self, interview_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """Delete an interview round enforcing tenant isolation."""
        interview = await self.get_interview(interview_id, user_id)
        await self.interview_repo.delete(interview)
        await self.session.commit()
        from app.services.analytics_service import AnalyticsService

        await AnalyticsService.invalidate_dashboard_cache(user_id)
