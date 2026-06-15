from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

ReportedCondition = Literal["rain", "no_rain", "storm"]
RainIntensity = Literal["light", "moderate", "heavy"]


class LocalWeatherReportCreate(BaseModel):
    location_name: str = Field(..., min_length=1, max_length=300)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    reported_condition: ReportedCondition = "rain"
    intensity: RainIntensity | None = "moderate"
    expires_in_minutes: int = Field(default=120, ge=15, le=240)

    @field_validator("location_name")
    @classmethod
    def normalize_location_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("intensity")
    @classmethod
    def clear_intensity_for_no_rain(cls, value: RainIntensity | None, info):
        if info.data.get("reported_condition") == "no_rain":
            return None
        return value or "moderate"


class LocalWeatherReportResponse(BaseModel):
    id: UUID
    user_id: UUID
    location_name: str
    latitude: float
    longitude: float
    reported_condition: str
    intensity: str | None
    source: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    expires_at: datetime

    class Config:
        from_attributes = True


class ClearLocalWeatherReportResponse(BaseModel):
    cleared: bool
