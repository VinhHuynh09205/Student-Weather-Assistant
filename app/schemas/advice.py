from datetime import date, time
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.models.domain import StudentAdviceReport

StudyShift = Literal["morning", "afternoon", "evening"]
VehicleType = Literal["motorbike", "bus", "walking", "bicycle"]

SHIFT_PRESETS: dict[StudyShift, tuple[time, time]] = {
    "morning": (time(7, 0), time(11, 0)),
    "afternoon": (time(13, 0), time(17, 0)),
    "evening": (time(18, 0), time(21, 0)),
}


class StudentAdviceRequest(BaseModel):
    city: str | None = Field(default=None, min_length=1)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    accuracy_meters: float | None = Field(default=None, ge=0)
    study_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None
    vehicle_type: VehicleType
    study_shift: StudyShift | None = None

    @model_validator(mode="after")
    def validate_study_schedule(self) -> "StudentAdviceRequest":
        if self.city is not None:
            self.city = self.city.strip()

        has_latitude = self.latitude is not None
        has_longitude = self.longitude is not None
        if has_latitude != has_longitude:
            raise ValueError("latitude và longitude phải được cung cấp cùng nhau.")

        if not (has_latitude and has_longitude) and not self.city:
            raise ValueError("Vui lòng cung cấp vị trí hiện tại hoặc tên thành phố.")

        if self.study_shift and (self.start_time is None or self.end_time is None):
            self.start_time, self.end_time = SHIFT_PRESETS[self.study_shift]

        if self.study_date is None:
            self.study_date = date.today()

        if self.start_time is None or self.end_time is None:
            raise ValueError("start_time và end_time là bắt buộc.")

        if self.end_time <= self.start_time:
            raise ValueError("Giờ kết thúc phải lớn hơn giờ bắt đầu.")

        return self

    @property
    def has_coordinates(self) -> bool:
        return self.latitude is not None and self.longitude is not None


class AdviceMetricsResponse(BaseModel):
    max_temperature_c: float
    max_apparent_temperature_c: float
    max_precipitation_probability_percent: int
    total_rain_mm: float
    max_wind_speed_kmh: float
    max_uv_index: float
    average_humidity_percent: float


class AdviceHourlyForecastResponse(BaseModel):
    time: str
    temperature_c: float
    weather_code: int
    precipitation_probability_percent: int
    weather_description: str
    wind_speed_kmh: float
    is_day: bool | None = None


class BeforeAfterClassTimelineResponse(BaseModel):
    time: str
    message: str
    temperature_c: float
    precipitation_probability_percent: int
    weather_description: str


class DuringClassTimelineResponse(BaseModel):
    time_range: str
    message: str
    max_temperature_c: float
    max_precipitation_probability_percent: int


class StudyTimelineResponse(BaseModel):
    before_class: BeforeAfterClassTimelineResponse
    during_class: DuringClassTimelineResponse
    after_class: BeforeAfterClassTimelineResponse


class StudentAdviceResponse(BaseModel):
    city: str
    source: str = "city"
    location_name: str
    display_name: str
    short_display_name: str | None = None
    administrative_levels: dict[str, str | None] | None = None
    country: str
    latitude: float
    longitude: float
    timezone: str | None = None
    accuracy_meters: float | None = None
    location_confidence: str = "exact"
    location_provider: str = "fallback"
    provider: str = "open_meteo"
    fallback_provider_used: bool = False
    fallback_provider: str | None = None
    needs_user_confirmation: bool = False
    location_candidates: list[str] = []
    study_date: str
    start_time: str
    end_time: str
    vehicle_type: VehicleType
    score: int
    level: str
    summary: str
    timeline: StudyTimelineResponse
    metrics: AdviceMetricsResponse
    recommendations: list[str]
    warnings: list[str]
    hourly_forecast: list[AdviceHourlyForecastResponse]
    weather_code: int
    weather_description: str
    is_day: bool | None = None
    time: str
    wind_speed_kmh: float
    precipitation_probability_percent: int
    temperature_c: float

    @classmethod
    def from_domain(cls, report: StudentAdviceReport) -> "StudentAdviceResponse":
        return cls(
            city=report.city,
            source=report.source,
            location_name=report.location_name,
            display_name=report.display_name or report.location_name,
            short_display_name=report.short_display_name,
            administrative_levels=report.administrative_levels,
            country=report.country,
            latitude=report.latitude,
            longitude=report.longitude,
            timezone=report.timezone,
            accuracy_meters=report.accuracy_meters,
            location_confidence=report.location_confidence,
            location_provider=report.location_provider,
            provider=report.provider,
            fallback_provider_used=report.fallback_provider_used,
            fallback_provider=report.fallback_provider,
            needs_user_confirmation=report.needs_user_confirmation,
            location_candidates=report.location_candidates or [],
            study_date=report.study_date,
            start_time=report.start_time,
            end_time=report.end_time,
            vehicle_type=report.vehicle_type,  # type: ignore[arg-type]
            score=report.score,
            level=report.level,
            summary=report.summary,
            timeline=StudyTimelineResponse(
                before_class=BeforeAfterClassTimelineResponse(
                    time=report.timeline.before_class.time,
                    message=report.timeline.before_class.message,
                    temperature_c=report.timeline.before_class.temperature_c,
                    precipitation_probability_percent=report.timeline.before_class.precipitation_probability_percent,
                    weather_description=report.timeline.before_class.weather_description,
                ),
                during_class=DuringClassTimelineResponse(
                    time_range=report.timeline.during_class.time_range,
                    message=report.timeline.during_class.message,
                    max_temperature_c=report.timeline.during_class.max_temperature_c,
                    max_precipitation_probability_percent=report.timeline.during_class.max_precipitation_probability_percent,
                ),
                after_class=BeforeAfterClassTimelineResponse(
                    time=report.timeline.after_class.time,
                    message=report.timeline.after_class.message,
                    temperature_c=report.timeline.after_class.temperature_c,
                    precipitation_probability_percent=report.timeline.after_class.precipitation_probability_percent,
                    weather_description=report.timeline.after_class.weather_description,
                ),
            ),
            metrics=AdviceMetricsResponse(
                max_temperature_c=report.metrics.max_temperature_c,
                max_apparent_temperature_c=report.metrics.max_apparent_temperature_c,
                max_precipitation_probability_percent=report.metrics.max_precipitation_probability_percent,
                total_rain_mm=report.metrics.total_rain_mm,
                max_wind_speed_kmh=report.metrics.max_wind_speed_kmh,
                max_uv_index=report.metrics.max_uv_index,
                average_humidity_percent=report.metrics.average_humidity_percent,
            ),
            recommendations=[recommendation for recommendation in report.recommendations],
            warnings=[warning for warning in report.warnings],
            hourly_forecast=[
                AdviceHourlyForecastResponse(
                    time=item.time,
                    temperature_c=item.temperature_c,
                    weather_code=item.weather_code,
                    precipitation_probability_percent=item.precipitation_probability_percent,
                    weather_description=item.weather_description,
                    wind_speed_kmh=item.wind_speed_kmh,
                    is_day=item.is_day,
                )
                for item in report.hourly_forecast
            ],
            weather_code=report.weather_code,
            weather_description=report.weather_description,
            is_day=report.is_day,
            time=report.time,
            wind_speed_kmh=report.wind_speed_kmh,
            precipitation_probability_percent=report.precipitation_probability_percent,
            temperature_c=report.temperature_c,
        )
