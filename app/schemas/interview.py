import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import InterviewStatus, InterviewType


class InterviewBase(BaseModel):
    """Base interview round attributes."""

    round_number: int = Field(ge=1)
    interview_type: InterviewType = InterviewType.TECHNICAL
    title: str = Field(min_length=1, max_length=100)
    scheduled_at: datetime
    duration_minutes: int | None = Field(default=None, ge=1, le=1440)
    meeting_url: str | None = Field(default=None, max_length=500)
    interviewer_names: str | None = Field(default=None, max_length=255)
    status: InterviewStatus = InterviewStatus.SCHEDULED
    feedback: str | None = None
    notes: str | None = None


class InterviewCreate(InterviewBase):
    """Schema for scheduling an interview round."""

    pass


class InterviewUpdate(BaseModel):
    """Schema for updating an interview round."""

    round_number: int | None = Field(default=None, ge=1)
    interview_type: InterviewType | None = None
    title: str | None = Field(default=None, min_length=1, max_length=100)
    scheduled_at: datetime | None = None
    duration_minutes: int | None = Field(default=None, ge=1, le=1440)
    meeting_url: str | None = Field(default=None, max_length=500)
    interviewer_names: str | None = Field(default=None, max_length=255)
    status: InterviewStatus | None = None
    feedback: str | None = None
    notes: str | None = None


class InterviewRead(InterviewBase):
    """Public interview round response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    application_id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
