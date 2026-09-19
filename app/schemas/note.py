import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import EntityType


class NoteBase(BaseModel):
    """Base note attributes."""

    entity_type: EntityType = EntityType.APPLICATION
    entity_id: uuid.UUID
    content: str = Field(min_length=1)


class NoteCreate(NoteBase):
    """Schema for creating a polymorphic rich note."""

    pass


class NoteRead(NoteBase):
    """Public note response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
