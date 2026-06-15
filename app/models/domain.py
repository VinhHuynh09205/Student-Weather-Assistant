from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Location:
    city: str
    country: str
    latitude: float
    longitude: float
    timezone: str
    source: str = "city"
    location_name: str | None = None
    display_name: str | None = None
    short_display_name: str | None = None
    administrative_levels: dict[str, str | None] | None = None
    accuracy_meters: float | None = None
    location_confidence: str = "exact"
    location_provider: str = "fallback"
    needs_user_confirmation: bool = False
    location_candidates: list[str] | None = None


@dataclass(frozen=True)
class WeatherSnapshot:
    time: str
    temperature_c: float
    apparent_temperature_c: float
    relative_humidity_percent: int
    precipitation_probability_percent: int | None
    precipitation_mm: float
    rain_mm: float
    weather_code: int
    weather_description: str
    wind_speed_kmh: float
    uv_index: float
    is_day: bool | None = None
    showers_mm: float | None = None
    wind_direction_degrees: int | None = None
    pressure_hpa: float | None = None
    visibility_meters: float | None = None
    cloud_cover_percent: int | None = None


@dataclass(frozen=True)
class CurrentWeatherReport:
    location: Location
    current: WeatherSnapshot
    provider: str = "open_meteo"
    fallback_provider_used: bool = False
    fallback_provider: str | None = None
    provider_condition: str | None = None
    effective_condition: str | None = None
    override_source: str | None = None
    override_expires_at: datetime | None = None
    override_report_id: str | None = None
    override_intensity: str | None = None
    provider_weather_code: int | None = None
    provider_weather_description: str | None = None


@dataclass(frozen=True)
class HourlyForecastReport:
    location: Location
    hourly: list[WeatherSnapshot]
    provider: str = "open_meteo"
    fallback_provider_used: bool = False
    fallback_provider: str | None = None


@dataclass(frozen=True)
class DailyForecast:
    date: str
    weather_code: int
    weather_description: str
    temperature_max_c: float
    temperature_min_c: float
    precipitation_probability_max_percent: int
    rain_sum_mm: float
    wind_speed_max_kmh: float
    uv_index_max: float
    sunrise: str
    sunset: str


@dataclass(frozen=True)
class DailyForecastReport:
    location: Location
    daily: list[DailyForecast]
    provider: str = "open_meteo"
    fallback_provider_used: bool = False
    fallback_provider: str | None = None


@dataclass(frozen=True)
class LocalWeatherOverride:
    id: str
    user_id: str
    location_name: str
    latitude: float
    longitude: float
    reported_condition: str
    intensity: str | None
    source: str
    created_at: datetime
    expires_at: datetime


@dataclass(frozen=True)
class AdviceMetrics:
    max_temperature_c: float
    max_apparent_temperature_c: float
    max_precipitation_probability_percent: int
    total_rain_mm: float
    max_wind_speed_kmh: float
    max_uv_index: float
    average_humidity_percent: float


@dataclass(frozen=True)
class AdviceHourlyForecast:
    time: str
    temperature_c: float
    weather_code: int
    precipitation_probability_percent: int
    weather_description: str
    wind_speed_kmh: float
    is_day: bool | None = None


@dataclass(frozen=True)
class BeforeAfterClassTimeline:
    time: str
    message: str
    temperature_c: float
    precipitation_probability_percent: int
    weather_description: str


@dataclass(frozen=True)
class DuringClassTimeline:
    time_range: str
    message: str
    max_temperature_c: float
    max_precipitation_probability_percent: int


@dataclass(frozen=True)
class StudyTimeline:
    before_class: BeforeAfterClassTimeline
    during_class: DuringClassTimeline
    after_class: BeforeAfterClassTimeline


@dataclass(frozen=True)
class StudentAdviceReport:
    city: str
    location_name: str
    country: str
    latitude: float
    longitude: float
    study_date: str
    start_time: str
    end_time: str
    vehicle_type: str
    score: int
    level: str
    summary: str
    timeline: StudyTimeline
    metrics: AdviceMetrics
    recommendations: list[str]
    warnings: list[str]
    hourly_forecast: list[AdviceHourlyForecast]
    weather_code: int
    weather_description: str
    is_day: bool | None
    time: str
    wind_speed_kmh: float
    precipitation_probability_percent: int
    temperature_c: float
    source: str = "city"
    display_name: str | None = None
    short_display_name: str | None = None
    administrative_levels: dict[str, str | None] | None = None
    timezone: str | None = None
    accuracy_meters: float | None = None
    location_confidence: str = "exact"
    location_provider: str = "fallback"
    provider: str = "open_meteo"
    fallback_provider_used: bool = False
    fallback_provider: str | None = None
    needs_user_confirmation: bool = False
    location_candidates: list[str] | None = None
    provider_condition: str | None = None
    effective_condition: str | None = None
    override_source: str | None = None
    override_expires_at: datetime | None = None
    override_report_id: str | None = None
    override_intensity: str | None = None
