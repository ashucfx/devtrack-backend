import hashlib
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import EntityAlreadyExistsException, UnauthorizedException
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.token import RefreshToken
from app.models.user import User
from app.repositories.token_repository import TokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.user import UserCreate, UserRead


def _hash_token(token: str) -> str:
    """Generate deterministic SHA-256 hash of a JWT for database storage and indexing."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class AuthService:
    """Service handling authentication, registration, token lifecycle, and revocation."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)
        self.token_repo = TokenRepository(session)
        self.settings = get_settings()

    async def register(self, user_in: UserCreate) -> tuple[User, TokenResponse]:
        """Register a new user and generate initial session tokens."""
        clean_email = user_in.email.lower().strip()
        if await self.user_repo.email_exists(clean_email):
            raise EntityAlreadyExistsException("User", "email", clean_email)

        user = User(
            email=clean_email,
            password_hash=hash_password(user_in.password),
            full_name=user_in.full_name.strip(),
            is_active=True,
            is_superuser=False,
        )
        user = await self.user_repo.create(user)

        tokens = await self._generate_session_tokens(user)
        await self.session.commit()
        return user, tokens

    async def login(self, credentials: LoginRequest) -> TokenResponse:
        """Authenticate user credentials and issue new session tokens."""
        clean_email = credentials.email.lower().strip()
        user = await self.user_repo.get_by_email(clean_email)

        if not user or not verify_password(credentials.password, user.password_hash):
            raise UnauthorizedException("Invalid email or password.")

        if not user.is_active:
            raise UnauthorizedException("User account is deactivated.")

        tokens = await self._generate_session_tokens(user)
        await self.session.commit()
        return tokens

    async def refresh_tokens(self, refresh_token_str: str) -> TokenResponse:
        """Rotate an existing valid refresh token for a new token pair."""
        payload = decode_token(refresh_token_str, expected_type="refresh")
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise UnauthorizedException("Invalid token payload.")

        token_hash = _hash_token(refresh_token_str)
        stored_token = await self.token_repo.get_active_by_hash(token_hash)
        if not stored_token:
            raise UnauthorizedException("Refresh token is invalid or has been revoked.")

        user = await self.user_repo.get_by_id(stored_token.user_id)
        if not user or not user.is_active:
            raise UnauthorizedException("User account is inactive or not found.")

        # Invalidate old refresh token (Token Rotation pattern)
        await self.token_repo.revoke_token(token_hash)

        # Issue new token pair
        tokens = await self._generate_session_tokens(user)
        await self.session.commit()
        return tokens

    async def logout(self, refresh_token_str: str) -> None:
        """Revoke a refresh token on user logout."""
        try:
            payload = decode_token(refresh_token_str, expected_type="refresh")
            if payload.get("sub"):
                token_hash = _hash_token(refresh_token_str)
                await self.token_repo.revoke_token(token_hash)
                await self.session.commit()
        except UnauthorizedException:
            # Idempotent logout - no error raised if token already expired/invalid
            pass

    async def _generate_session_tokens(self, user: User) -> TokenResponse:
        """Internal helper to generate access/refresh tokens and persist refresh token hash."""
        access_token = create_access_token(subject=user.id)
        refresh_token = create_refresh_token(subject=user.id)

        token_hash = _hash_token(refresh_token)
        expires_at = datetime.now(UTC) + timedelta(days=self.settings.REFRESH_TOKEN_EXPIRE_DAYS)

        db_token = RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
            is_revoked=False,
        )
        await self.token_repo.create(db_token)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=UserRead.model_validate(user),
        )
