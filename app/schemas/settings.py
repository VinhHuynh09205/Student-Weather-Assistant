from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class SettingsBase(BaseModel):
    temperature_unit: str = "celsius"  # celsius, fahrenheit
    theme_mode: str = "auto"  # auto, light, dark
    auto_refresh_enabled: bool = True
    notification_enabled: bool = True
    default_vehicle_type: str = "motorbike"
    default_location_id: UUID | None = None


class SettingsUpdate(BaseModel):
    temperature_unit: str | None = None
    theme_mode: str | None = None
    auto_refresh_enabled: bool | None = None
    notification_enabled: bool | None = None
    default_vehicle_type: str | None = None
    default_location_id: UUID | None = None


class SettingsResponse(SettingsBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
