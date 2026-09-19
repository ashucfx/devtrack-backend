import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CompanyBase(BaseModel):
    """Base company properties shared across schemas."""

    name: str = Field(min_length=1, max_length=100)
    website: str | None = Field(default=None, max_length=255)
    industry: str | None = Field(default=None, max_length=100)
    location: str | None = Field(default=None, max_length=100)
    notes: str | None = None


class CompanyCreate(CompanyBase):
    """Schema for creating a new company record."""

    pass


class CompanyUpdate(BaseModel):
    """Schema for updating an existing company record."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    website: str | None = Field(default=None, max_length=255)
    industry: str | None = Field(default=None, max_length=100)
    location: str | None = Field(default=None, max_length=100)
    notes: str | None = None


class CompanyRead(CompanyBase):
    """Public company response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
