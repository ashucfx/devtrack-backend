import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import ApplicationStage


class StageTransitionRequest(BaseModel):
    """Schema for transitioning an application to a new stage."""

    to_stage: ApplicationStage
    notes: str | None = Field(default=None, max_length=1000)


class StageHistoryRead(BaseModel):
    """Public application stage transition record schema."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    application_id: uuid.UUID
    from_stage: str | None
    to_stage: str
    notes: str | None
    changed_at: datetime


class ApplicationTimelineResponse(BaseModel):
    """Timeline summary response schema."""

    application_id: uuid.UUID
    current_stage: str
    timeline: list[StageHistoryRead]
