from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class NotificationBase(BaseModel):
    type: str
    title: str
    message: str
    channel: str  # email | web | in_app | browser
    scheduled_for: datetime | None = None


class NotificationCreate(NotificationBase):
    user_id: UUID
    schedule_id: UUID | None = None


class NotificationUpdate(BaseModel):
    status: str | None = None
    sent_at: datetime | None = None
    error_message: str | None = None
    read_at: datetime | None = None


class NotificationResponse(NotificationBase):
    id: UUID
    user_id: UUID
    schedule_id: UUID | None
    status: str
    error_message: str | None
    sent_at: datetime | None
    read_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TestNotificationResponse(BaseModel):
    notification_id: UUID
    channels_attempted: list[str]
    channels_succeeded: list[str]
    channels_failed: list[str]
    message: str
