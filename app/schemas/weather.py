from pydantic import BaseModel

from app.models.domain import (
    CurrentWeatherReport,
    DailyForecastReport,
    HourlyForecastReport,
)


class CurrentWeather(BaseModel):
    temperature_c: float
    apparent_temperature_c: float
    relative_humidity_percent: int
    precipitation_probability_percent: int | None = None
    precipitation_mm: float
    rain_mm: float
    showers_mm: float | None = None
    weather_code: int
    weather_description: str
    wind_speed_kmh: float
    wind_direction_degrees: int | None = None
    uv_index: float
    pressure_hpa: float | None = None
    visibility_meters: float | None = None
    cloud_cover_percent: int | None = None
    time: str
    is_day: bool | None = None


class CurrentWeatherResponse(BaseModel):
    city: str
    source: str = "city"
    location_name: str
    display_name: str
    short_display_name: str | None = None
    administrative_levels: dict[str, str | None] | None = None
    country: str
    latitude: float
    longitude: float
    timezone: str
    accuracy_meters: float | None = None
    location_confidence: str = "exact"
    location_provider: str = "fallback"
    provider: str = "open_meteo"
    fallback_provider_used: bool = False
    fallback_provider: str | None = None
    needs_user_confirmation: bool = False
    location_candidates: list[str] = []
    current: CurrentWeather

    @classmethod
    def from_domain(cls, report: CurrentWeatherReport) -> "CurrentWeatherResponse":
        location = report.location
        return cls(
            city=location.city,
            source=location.source,
            location_name=location.location_name or location.city,
            display_name=location.display_name or location.location_name or location.city,
            short_display_name=location.short_display_name,
            administrative_levels=location.administrative_levels,
            country=location.country,
            latitude=location.latitude,
            longitude=location.longitude,
            timezone=location.timezone,
            accuracy_meters=location.accuracy_meters,
            location_confidence=location.location_confidence,
            location_provider=location.location_provider,
            needs_user_confirmation=location.needs_user_confirmation,
            location_candidates=location.location_candidates or [],
            provider=report.provider,
            fallback_provider_used=report.fallback_provider_used,
            fallback_provider=report.fallback_provider,
            current=CurrentWeather(
                temperature_c=report.current.temperature_c,
                apparent_temperature_c=report.current.apparent_temperature_c,
                relative_humidity_percent=report.current.relative_humidity_percent,
                precipitation_probability_percent=report.current.precipitation_probability_percent,
                precipitation_mm=report.current.precipitation_mm,
                rain_mm=report.current.rain_mm,
                showers_mm=report.current.showers_mm,
                weather_code=report.current.weather_code,
                weather_description=report.current.weather_description,
                wind_speed_kmh=report.current.wind_speed_kmh,
                wind_direction_degrees=report.current.wind_direction_degrees,
                uv_index=report.current.uv_index,
                pressure_hpa=report.current.pressure_hpa,
                visibility_meters=report.current.visibility_meters,
                cloud_cover_percent=report.current.cloud_cover_percent,
                time=report.current.time,
                is_day=report.current.is_day,
            ),
        )


class HourlyWeather(BaseModel):
    time: str
    temperature_c: float
    apparent_temperature_c: float
    relative_humidity_percent: int
    precipitation_probability_percent: int
    precipitation_mm: float
    rain_mm: float
    weather_code: int
    weather_description: str
    wind_speed_kmh: float
    uv_index: float
    is_day: bool | None = None


class HourlyForecastResponse(BaseModel):
    city: str
    source: str = "city"
    location_name: str
    display_name: str
    short_display_name: str | None = None
    administrative_levels: dict[str, str | None] | None = None
    country: str
    latitude: float
    longitude: float
    timezone: str
    accuracy_meters: float | None = None
    location_confidence: str = "exact"
    location_provider: str = "fallback"
    provider: str = "open_meteo"
    fallback_provider_used: bool = False
    fallback_provider: str | None = None
    needs_user_confirmation: bool = False
    location_candidates: list[str] = []
    hourly: list[HourlyWeather]

    @classmethod
    def from_domain(cls, report: HourlyForecastReport) -> "HourlyForecastResponse":
        return cls(
            city=report.location.city,
            source=report.location.source,
            location_name=report.location.location_name or report.location.city,
            display_name=report.location.display_name or report.location.location_name or report.location.city,
            short_display_name=report.location.short_display_name,
            administrative_levels=report.location.administrative_levels,
            country=report.location.country,
            latitude=report.location.latitude,
            longitude=report.location.longitude,
            timezone=report.location.timezone,
            accuracy_meters=report.location.accuracy_meters,
            location_confidence=report.location.location_confidence,
            location_provider=report.location.location_provider,
            needs_user_confirmation=report.location.needs_user_confirmation,
            location_candidates=report.location.location_candidates or [],
            provider=report.provider,
            fallback_provider_used=report.fallback_provider_used,
            fallback_provider=report.fallback_provider,
            hourly=[
                HourlyWeather(
                    time=item.time,
                    temperature_c=item.temperature_c,
                    apparent_temperature_c=item.apparent_temperature_c,
                    relative_humidity_percent=item.relative_humidity_percent,
                    precipitation_probability_percent=item.precipitation_probability_percent or 0,
                    precipitation_mm=item.precipitation_mm,
                    rain_mm=item.rain_mm,
                    weather_code=item.weather_code,
                    weather_description=item.weather_description,
                    wind_speed_kmh=item.wind_speed_kmh,
                    uv_index=item.uv_index,
                    is_day=item.is_day,
                )
                for item in report.hourly
            ],
        )


class DailyWeather(BaseModel):
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


class DailyForecastResponse(BaseModel):
    city: str
    source: str = "city"
    location_name: str
    display_name: str
    short_display_name: str | None = None
    administrative_levels: dict[str, str | None] | None = None
    country: str
    latitude: float
    longitude: float
    timezone: str
    accuracy_meters: float | None = None
    location_confidence: str = "exact"
    location_provider: str = "fallback"
    provider: str = "open_meteo"
    fallback_provider_used: bool = False
    fallback_provider: str | None = None
    needs_user_confirmation: bool = False
    location_candidates: list[str] = []
    daily: list[DailyWeather]

    @classmethod
    def from_domain(cls, report: DailyForecastReport) -> "DailyForecastResponse":
        return cls(
            city=report.location.city,
            source=report.location.source,
            location_name=report.location.location_name or report.location.city,
            display_name=report.location.display_name or report.location.location_name or report.location.city,
            short_display_name=report.location.short_display_name,
            administrative_levels=report.location.administrative_levels,
            country=report.location.country,
            latitude=report.location.latitude,
            longitude=report.location.longitude,
            timezone=report.location.timezone,
            accuracy_meters=report.location.accuracy_meters,
            location_confidence=report.location.location_confidence,
            location_provider=report.location.location_provider,
            needs_user_confirmation=report.location.needs_user_confirmation,
            location_candidates=report.location.location_candidates or [],
            provider=report.provider,
            fallback_provider_used=report.fallback_provider_used,
            fallback_provider=report.fallback_provider,
            daily=[
                DailyWeather(
                    date=item.date,
                    weather_code=item.weather_code,
                    weather_description=item.weather_description,
                    temperature_max_c=item.temperature_max_c,
                    temperature_min_c=item.temperature_min_c,
                    precipitation_probability_max_percent=item.precipitation_probability_max_percent,
                    rain_sum_mm=item.rain_sum_mm,
                    wind_speed_max_kmh=item.wind_speed_max_kmh,
                    uv_index_max=item.uv_index_max,
                    sunrise=item.sunrise,
                    sunset=item.sunset,
                )
                for item in report.daily
            ],
        )


class SearchLocationResponse(BaseModel):
    city: str
    country: str
    latitude: float
    longitude: float
    timezone: str
    display_name: str
    short_display_name: str | None = None
    administrative_levels: dict[str, str | None] | None = None
    location_confidence: str
    location_provider: str
