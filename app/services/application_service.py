import math
import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EntityNotFoundException
from app.models.application import Application
from app.repositories.application_repository import ApplicationRepository
from app.repositories.company_repository import CompanyRepository
from app.schemas.application import ApplicationCreate, ApplicationRead, ApplicationUpdate
from app.schemas.common import PaginatedResponse


class ApplicationService:
    """Service handling job application business logic and ownership validation."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.app_repo = ApplicationRepository(session)
        self.company_repo = CompanyRepository(session)

    async def create_application(
        self, app_in: ApplicationCreate, user_id: uuid.UUID
    ) -> Application:
        """Create a job application record after verifying company tenant ownership."""
        company = await self.company_repo.get_by_id_and_user(app_in.company_id, user_id)
        if not company:
            raise EntityNotFoundException("Company", app_in.company_id)

        application = Application(
            user_id=user_id,
            company_id=app_in.company_id,
            job_title=app_in.job_title.strip(),
            job_url=app_in.job_url.strip() if app_in.job_url else None,
            employment_type=app_in.employment_type,
            location=app_in.location.strip() if app_in.location else None,
            location_type=app_in.location_type,
            salary_min=app_in.salary_min,
            salary_max=app_in.salary_max,
            currency=app_in.currency.upper().strip(),
            source=app_in.source,
            applied_date=app_in.applied_date,
            current_stage=app_in.current_stage,
            status=app_in.status,
            priority=app_in.priority,
            notes=app_in.notes.strip() if app_in.notes else None,
        )
        application = await self.app_repo.create(application)
        await self.session.commit()

        # Reload with joined company
        return await self.get_application(application.id, user_id)

    async def get_application(self, application_id: uuid.UUID, user_id: uuid.UUID) -> Application:
        """Retrieve an application ensuring it belongs to the authenticated user."""
        application = await self.app_repo.get_by_id_and_user(application_id, user_id)
        if not application:
            raise EntityNotFoundException("Application", application_id)
        return application

    async def list_applications(
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
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[ApplicationRead]:
        """List user applications with database-level filtering, sorting, and pagination."""
        offset = (page - 1) * page_size
        items = await self.app_repo.list_by_user(
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
            sort_by=sort_by,
            sort_order=sort_order,
            offset=offset,
            limit=page_size,
        )
        total = await self.app_repo.count_by_user(
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
        total_pages = math.ceil(total / page_size) if total > 0 else 1

        return PaginatedResponse[ApplicationRead](
            items=[ApplicationRead.model_validate(item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def update_application(
        self,
        application_id: uuid.UUID,
        app_update: ApplicationUpdate,
        user_id: uuid.UUID,
    ) -> Application:
        """Update an application verifying tenant ownership of both application and new company."""
        application = await self.get_application(application_id, user_id)

        update_dict = app_update.model_dump(exclude_unset=True)
        if "company_id" in update_dict and update_dict["company_id"] is not None:
            new_comp_id = update_dict["company_id"]
            if new_comp_id != application.company_id:
                company = await self.company_repo.get_by_id_and_user(new_comp_id, user_id)
                if not company:
                    raise EntityNotFoundException("Company", new_comp_id)

        if update_dict.get("job_title"):
            update_dict["job_title"] = update_dict["job_title"].strip()

        if update_dict:
            await self.app_repo.update(application, **update_dict)
            await self.session.commit()

        return await self.get_application(application.id, user_id)

    async def delete_application(self, application_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """Delete an application record enforcing tenant isolation."""
        application = await self.get_application(application_id, user_id)
        await self.app_repo.delete(application)
        await self.session.commit()
