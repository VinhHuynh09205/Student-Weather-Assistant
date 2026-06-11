from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class LocationBase(BaseModel):
    label: str = Field(..., max_length=50)
    display_name: str
    short_display_name: str | None = None
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    source: str = "user_confirmed"  # gps, search, user_confirmed
    administrative_levels: dict[str, Any] | None = None
    is_default: bool = False


class LocationCreate(LocationBase):
    pass


class LocationUpdate(BaseModel):
    label: str | None = Field(None, max_length=50)
    display_name: str | None = None
    short_display_name: str | None = None
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    source: str | None = None
    administrative_levels: dict[str, Any] | None = None
    is_default: bool | None = None


class LocationResponse(LocationBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
