from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

VehicleType = Literal["motorbike", "bus", "walking", "car", "bicycle"]


class ScheduleBase(BaseModel):
    title: str = Field(..., max_length=100)
    study_date: str | None = None  # YYYY-MM-DD
    start_time: str  # HH:MM
    end_time: str  # HH:MM
    vehicle_type: VehicleType = "motorbike"
    location_id: UUID | None = None
    repeat_type: str = "none"  # none, weekly
    repeat_days: list[str] | None = None  # e.g., ["mon", "wed", "fri"]
    note: str | None = None
    is_active: bool = True

    @field_validator("vehicle_type", mode="before")
    @classmethod
    def normalize_vehicle_type(cls, value: object) -> object:
        if value == "walk":
            return "walking"
        return value


class ScheduleCreate(ScheduleBase):
    pass


class ScheduleUpdate(BaseModel):
    title: str | None = Field(None, max_length=100)
    study_date: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    vehicle_type: VehicleType | None = None
    location_id: UUID | None = None
    repeat_type: str | None = None
    repeat_days: list[str] | None = None
    note: str | None = None
    is_active: bool | None = None

    @field_validator("vehicle_type", mode="before")
    @classmethod
    def normalize_vehicle_type(cls, value: object) -> object:
        if value == "walk":
            return "walking"
        return value


class ScheduleResponse(ScheduleBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
