import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EntityAlreadyExistsException, EntityNotFoundException
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserUpdate


class UserService:
    """Service handling user domain business logic."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)

    async def get_user_by_id(self, user_id: uuid.UUID) -> User:
        """Retrieve user by ID or raise EntityNotFoundException."""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise EntityNotFoundException("User", user_id)
        return user

    async def update_profile(self, user_id: uuid.UUID, update_data: UserUpdate) -> User:
        """Update authenticated user's profile information."""
        user = await self.get_user_by_id(user_id)

        update_dict = update_data.model_dump(exclude_unset=True)
        if "email" in update_dict and update_dict["email"] is not None:
            new_email = update_dict["email"].lower().strip()
            if new_email != user.email:
                if await self.user_repo.email_exists(new_email):
                    raise EntityAlreadyExistsException("User", "email", new_email)
                update_dict["email"] = new_email

        if update_dict:
            user = await self.user_repo.update(user, **update_dict)
            await self.session.commit()

        return user
