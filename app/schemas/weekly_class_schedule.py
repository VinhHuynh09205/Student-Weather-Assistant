from datetime import date, datetime, time
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.advice import VehicleType

RiskLevel = Literal["SAFE", "NOTICE", "PREPARE", "DANGER"]
ForecastStatus = Literal["available", "pending", "expired", "missing_location", "unavailable", "error"]


class WeeklyClassScheduleBase(BaseModel):
    subject_name: str = Field(..., min_length=1, max_length=120)
    day_of_week: int = Field(..., ge=0, le=6)
    start_time: time
    end_time: time
    vehicle_type: VehicleType = "motorbike"
    location_name: str | None = Field(default=None, max_length=255)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    timezone: str = Field(default="Asia/Ho_Chi_Minh", min_length=1, max_length=64)
    is_active: bool = True
    notify_before_minutes: int = Field(default=60, ge=0)
    rain_alert_enabled: bool = True
    storm_alert_enabled: bool = True
    semester_start_date: date | None = None
    semester_end_date: date | None = None

    @field_validator("vehicle_type", mode="before")
    @classmethod
    def normalize_vehicle_type(cls, value: object) -> object:
        if value == "walk":
            return "walking"
        return value

    @model_validator(mode="after")
    def validate_schedule(self) -> "WeeklyClassScheduleBase":
        self.subject_name = self.subject_name.strip()
        if not self.subject_name:
            raise ValueError("subject_name khong duoc rong.")

        if self.location_name is not None:
            self.location_name = self.location_name.strip() or None

        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude va longitude phai duoc cung cap cung nhau.")

        if self.start_time >= self.end_time:
            raise ValueError("start_time phai truoc end_time.")

        if (
            self.semester_start_date is not None
            and self.semester_end_date is not None
            and self.semester_start_date > self.semester_end_date
        ):
            raise ValueError("semester_start_date khong duoc sau semester_end_date.")

        return self


class WeeklyClassScheduleCreate(WeeklyClassScheduleBase):
    pass


class WeeklyClassScheduleUpdate(BaseModel):
    subject_name: str | None = Field(default=None, min_length=1, max_length=120)
    day_of_week: int | None = Field(default=None, ge=0, le=6)
    start_time: time | None = None
    end_time: time | None = None
    vehicle_type: VehicleType | None = None
    location_name: str | None = Field(default=None, max_length=255)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    timezone: str | None = Field(default=None, min_length=1, max_length=64)
    is_active: bool | None = None
    notify_before_minutes: int | None = Field(default=None, ge=0)
    rain_alert_enabled: bool | None = None
    storm_alert_enabled: bool | None = None
    semester_start_date: date | None = None
    semester_end_date: date | None = None

    @field_validator("vehicle_type", mode="before")
    @classmethod
    def normalize_vehicle_type(cls, value: object) -> object:
        if value == "walk":
            return "walking"
        return value

    @model_validator(mode="after")
    def validate_partial_schedule(self) -> "WeeklyClassScheduleUpdate":
        if self.subject_name is not None:
            self.subject_name = self.subject_name.strip()
            if not self.subject_name:
                raise ValueError("subject_name khong duoc rong.")

        if self.location_name is not None:
            self.location_name = self.location_name.strip() or None

        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude va longitude phai duoc cung cap cung nhau.")

        return self


class WeeklyClassScheduleResponse(WeeklyClassScheduleBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DeleteWeeklyClassScheduleResponse(BaseModel):
    success: bool = True
    message: str
    schedule_id: UUID
    is_active: bool


class ClassScheduleOccurrenceResponse(BaseModel):
    occurrence_key: str
    start_datetime: datetime
    end_datetime: datetime
    status: Literal["scheduled", "expired"] = "scheduled"


class ClassScheduleTimelineAdviceResponse(BaseModel):
    before_class: str
    during_class: str
    after_class: str


class ClassScheduleForecastResponse(BaseModel):
    schedule: WeeklyClassScheduleResponse
    next_occurrence: ClassScheduleOccurrenceResponse | None
    next_occurrence_datetime: datetime | None = None
    forecast_status: ForecastStatus
    weather_summary: str | None = None
    risk_level: RiskLevel
    recommendation_message: str
    weather_code: int | None = None
    precipitation_probability_percent: int | None = None
    rain_mm: float | None = None
    wind_speed_kmh: float | None = None
    provider: str | None = None
    study_score: int | None = None
    commute_score: int | None = None
    score_label: str | None = None
    summary_message: str | None = None
    weather_warning: str | None = None
    commute_advice: str | None = None
    preparation_items: list[str] = Field(default_factory=list)
    reason_factors: list[str] = Field(default_factory=list)
    timeline_advice: ClassScheduleTimelineAdviceResponse | None = None
    vehicle_type: VehicleType = "motorbike"
    provider_condition: str | None = None
    effective_condition: str | None = None
    override_source: str | None = None
    override_expires_at: datetime | None = None
    override_report_id: str | None = None
    override_intensity: str | None = None
