import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EntityAlreadyExistsException, EntityNotFoundException
from app.models.user import User
from app.schemas.company import CompanyCreate, CompanyUpdate
from app.services.company_service import CompanyService


@pytest.mark.asyncio
async def test_create_company_success(db_session: AsyncSession, test_user: User) -> None:
    service = CompanyService(db_session)
    company_in = CompanyCreate(
        name="Google",
        website="https://google.com",
        industry="Technology",
        location="Mountain View, CA",
        notes="Applied for Staff Backend Engineer",
    )
    company = await service.create_company(company_in, test_user.id)
    assert company.id is not None
    assert company.name == "Google"
    assert company.user_id == test_user.id


@pytest.mark.asyncio
async def test_create_company_duplicate_name_for_same_user(
    db_session: AsyncSession, test_user: User
) -> None:
    service = CompanyService(db_session)
    company_in = CompanyCreate(name="Meta")
    await service.create_company(company_in, test_user.id)

    # Creating company with same name for same user must fail
    with pytest.raises(EntityAlreadyExistsException):
        await service.create_company(company_in, test_user.id)


@pytest.mark.asyncio
async def test_create_company_same_name_different_users_allowed(
    db_session: AsyncSession, test_user: User
) -> None:
    service = CompanyService(db_session)
    user2_id = uuid.uuid4()

    company_in = CompanyCreate(name="Stripe")
    comp1 = await service.create_company(company_in, test_user.id)
    comp2 = await service.create_company(company_in, user2_id)

    assert comp1.name == comp2.name
    assert comp1.user_id != comp2.user_id


@pytest.mark.asyncio
async def test_get_company_not_found(db_session: AsyncSession, test_user: User) -> None:
    service = CompanyService(db_session)
    with pytest.raises(EntityNotFoundException):
        await service.get_company(uuid.uuid4(), test_user.id)


@pytest.mark.asyncio
async def test_update_company_and_delete(db_session: AsyncSession, test_user: User) -> None:
    service = CompanyService(db_session)
    company = await service.create_company(CompanyCreate(name="Amazon"), test_user.id)

    updated = await service.update_company(
        company.id, CompanyUpdate(location="Seattle, WA"), test_user.id
    )
    assert updated.location == "Seattle, WA"

    await service.delete_company(company.id, test_user.id)
    with pytest.raises(EntityNotFoundException):
        await service.get_company(company.id, test_user.id)
