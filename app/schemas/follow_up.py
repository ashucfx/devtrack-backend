import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import FollowUpStatus


class FollowUpBase(BaseModel):
    """Base follow-up reminder attributes."""

    title: str = Field(min_length=1, max_length=100)
    due_date: date
    status: FollowUpStatus = FollowUpStatus.PENDING
    notes: str | None = None


class FollowUpCreate(FollowUpBase):
    """Schema for scheduling a follow-up task."""

    pass


class FollowUpUpdate(BaseModel):
    """Schema for updating follow-up details or completion status."""

    title: str | None = Field(default=None, min_length=1, max_length=100)
    due_date: date | None = None
    status: FollowUpStatus | None = None
    notes: str | None = None


class FollowUpRead(FollowUpBase):
    """Public follow-up task response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    application_id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
