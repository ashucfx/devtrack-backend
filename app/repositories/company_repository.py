import uuid
from collections.abc import Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.repositories.base import BaseRepository


class CompanyRepository(BaseRepository[Company]):
    """Repository handling database operations for Company entity with tenant isolation."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Company, session)

    async def get_by_id_and_user(self, company_id: uuid.UUID, user_id: uuid.UUID) -> Company | None:
        """Fetch a single company record verifying user ownership."""
        stmt = select(Company).where(
            Company.id == company_id,
            Company.user_id == user_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name_and_user(self, name: str, user_id: uuid.UUID) -> Company | None:
        """Fetch company by case-insensitive name within user scope."""
        stmt = select(Company).where(
            Company.user_id == user_id,
            func.lower(Company.name) == name.lower().strip(),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def name_exists_for_user(
        self, name: str, user_id: uuid.UUID, exclude_id: uuid.UUID | None = None
    ) -> bool:
        """Check if a company name is already registered for this user."""
        stmt = select(Company.id).where(
            Company.user_id == user_id,
            func.lower(Company.name) == name.lower().strip(),
        )
        if exclude_id:
            stmt = stmt.where(Company.id != exclude_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def list_by_user(
        self,
        user_id: uuid.UUID,
        search: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> Sequence[Company]:
        """List companies owned by user with optional ILIKE search and pagination."""
        stmt = select(Company).where(Company.user_id == user_id)

        if search and search.strip():
            pattern = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    Company.name.ilike(pattern),
                    Company.industry.ilike(pattern),
                    Company.location.ilike(pattern),
                )
            )

        stmt = stmt.order_by(Company.name.asc()).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_by_user(
        self,
        user_id: uuid.UUID,
        search: str | None = None,
    ) -> int:
        """Count total companies owned by user with optional search filter."""
        stmt = select(func.count(Company.id)).where(Company.user_id == user_id)

        if search and search.strip():
            pattern = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    Company.name.ilike(pattern),
                    Company.industry.ilike(pattern),
                    Company.location.ilike(pattern),
                )
            )

        result = await self.session.execute(stmt)
        return result.scalar_one() or 0
