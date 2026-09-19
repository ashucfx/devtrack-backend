import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EntityNotFoundException
from app.models.user import User
from app.schemas.user import UserUpdate
from app.services.user_service import UserService


@pytest.mark.asyncio
async def test_get_user_by_id_found(db_session: AsyncSession, test_user: User) -> None:
    service = UserService(db_session)
    user = await service.get_user_by_id(test_user.id)
    assert user.id == test_user.id
    assert user.email == test_user.email


@pytest.mark.asyncio
async def test_get_user_by_id_not_found(db_session: AsyncSession) -> None:
    service = UserService(db_session)
    random_id = uuid.uuid4()
    with pytest.raises(EntityNotFoundException):
        await service.get_user_by_id(random_id)


@pytest.mark.asyncio
async def test_update_profile_empty_payload(db_session: AsyncSession, test_user: User) -> None:
    service = UserService(db_session)
    user = await service.update_profile(test_user.id, UserUpdate())
    assert user.full_name == test_user.full_name
