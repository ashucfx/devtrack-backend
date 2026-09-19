import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import NotificationType


class NotificationBase(BaseModel):
    """Base notification attributes."""

    notification_type: NotificationType = NotificationType.FOLLOW_UP_DUE
    title: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1)


class NotificationCreate(NotificationBase):
    """Schema for dispatching a notification."""

    pass


class NotificationRead(NotificationBase):
    """Public notification response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    is_read: bool
    created_at: datetime
    updated_at: datetime
