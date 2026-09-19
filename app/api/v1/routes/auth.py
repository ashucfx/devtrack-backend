from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.database import get_db
from app.core.config import get_settings
from app.core.rate_limiter import RateLimiter
from app.schemas.auth import LoginRequest, RefreshTokenRequest, TokenResponse
from app.schemas.common import ErrorResponse
from app.schemas.user import UserCreate
from app.services.auth_service import AuthService

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["Authentication"])

login_rate_limiter = RateLimiter(
    max_requests=settings.RATE_LIMIT_LOGIN_MAX_REQUESTS,
    window_seconds=settings.RATE_LIMIT_LOGIN_WINDOW_SECONDS,
    key_prefix="login",
)
register_rate_limiter = RateLimiter(
    max_requests=settings.RATE_LIMIT_REGISTER_MAX_REQUESTS,
    window_seconds=settings.RATE_LIMIT_REGISTER_WINDOW_SECONDS,
    key_prefix="register",
)


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
    dependencies=[Depends(register_rate_limiter)],
    responses={
        409: {"model": ErrorResponse, "description": "Email already registered"},
        422: {"model": ErrorResponse, "description": "Validation error"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
)
async def register(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Register a new user account and receive authentication tokens."""
    service = AuthService(db)
    _, tokens = await service.register(user_in)
    return tokens


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate and obtain tokens",
    dependencies=[Depends(login_rate_limiter)],
    responses={
        401: {"model": ErrorResponse, "description": "Invalid credentials"},
        422: {"model": ErrorResponse, "description": "Validation error"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
)
async def login(
    credentials: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate with email and password to receive access and refresh tokens."""
    service = AuthService(db)
    return await service.login(credentials)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Rotate refresh token for new access and refresh tokens",
    responses={
        401: {"model": ErrorResponse, "description": "Invalid or expired refresh token"},
    },
)
async def refresh_token(
    refresh_in: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Rotate a valid refresh token for a brand new access and refresh token pair."""
    service = AuthService(db)
    return await service.refresh_tokens(refresh_in.refresh_token)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke active refresh token",
)
async def logout(
    refresh_in: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Revoke the given refresh token, effectively terminating the session."""
    service = AuthService(db)
    await service.logout(refresh_in.refresh_token)
