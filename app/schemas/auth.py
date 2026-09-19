from pydantic import BaseModel, EmailStr, Field

from app.schemas.user import UserRead


class LoginRequest(BaseModel):
    """Schema for user credentials authentication."""

    email: EmailStr
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    """Schema for JWT authentication tokens response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserRead


class RefreshTokenRequest(BaseModel):
    """Schema for refreshing access tokens."""

    refresh_token: str = Field(min_length=1)


class PasswordChangeRequest(BaseModel):
    """Schema for changing user password."""

    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)
