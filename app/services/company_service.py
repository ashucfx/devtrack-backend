import math
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EntityAlreadyExistsException, EntityNotFoundException
from app.models.company import Company
from app.repositories.company_repository import CompanyRepository
from app.schemas.common import PaginatedResponse
from app.schemas.company import CompanyCreate, CompanyRead, CompanyUpdate


class CompanyService:
    """Service handling company lifecycle and multi-tenant data isolation."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.company_repo = CompanyRepository(session)

    async def create_company(self, company_in: CompanyCreate, user_id: uuid.UUID) -> Company:
        """Create a new company record within the authenticated user's scope."""
        clean_name = company_in.name.strip()
        if await self.company_repo.name_exists_for_user(clean_name, user_id):
            raise EntityAlreadyExistsException("Company", "name", clean_name)

        company = Company(
            user_id=user_id,
            name=clean_name,
            website=company_in.website.strip() if company_in.website else None,
            industry=company_in.industry.strip() if company_in.industry else None,
            location=company_in.location.strip() if company_in.location else None,
            notes=company_in.notes.strip() if company_in.notes else None,
        )
        company = await self.company_repo.create(company)
        await self.session.commit()
        return company

    async def get_company(self, company_id: uuid.UUID, user_id: uuid.UUID) -> Company:
        """Retrieve a specific company ensuring the requesting user is the owner."""
        company = await self.company_repo.get_by_id_and_user(company_id, user_id)
        if not company:
            raise EntityNotFoundException("Company", company_id)
        return company

    async def list_companies(
        self,
        user_id: uuid.UUID,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[CompanyRead]:
        """List companies owned by the authenticated user with search and pagination."""
        offset = (page - 1) * page_size
        items = await self.company_repo.list_by_user(
            user_id=user_id,
            search=search,
            offset=offset,
            limit=page_size,
        )
        total = await self.company_repo.count_by_user(user_id=user_id, search=search)
        total_pages = math.ceil(total / page_size) if total > 0 else 1

        return PaginatedResponse[CompanyRead](
            items=[CompanyRead.model_validate(item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def update_company(
        self,
        company_id: uuid.UUID,
        company_update: CompanyUpdate,
        user_id: uuid.UUID,
    ) -> Company:
        """Update an existing company record verifying tenant ownership and uniqueness."""
        company = await self.get_company(company_id, user_id)

        update_dict = company_update.model_dump(exclude_unset=True)
        if "name" in update_dict and update_dict["name"] is not None:
            clean_name = update_dict["name"].strip()
            if (
                clean_name.lower() != company.name.lower()
                and await self.company_repo.name_exists_for_user(
                    clean_name, user_id, exclude_id=company.id
                )
            ):
                raise EntityAlreadyExistsException("Company", "name", clean_name)
            update_dict["name"] = clean_name

        if update_dict:
            company = await self.company_repo.update(company, **update_dict)
            await self.session.commit()

        return company

    async def delete_company(self, company_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """Delete a company record ensuring ownership isolation."""
        company = await self.get_company(company_id, user_id)
        await self.company_repo.delete(company)
        await self.session.commit()
