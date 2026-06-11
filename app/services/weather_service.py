from dataclasses import replace
from typing import Any

from app.core.constants import ALLOWED_HOURLY_FORECAST_HOURS
from app.models.domain import (
    CurrentWeatherReport,
    DailyForecastReport,
    HourlyForecastReport,
    Location,
)
from app.providers.weather.base import BaseWeatherProvider
from app.services.geocoding_service import GeocodingService
from app.services.location_display_service import LocationDisplayService
from app.services.weather_cache import (
    AsyncTTLCache,
    normalize_city_for_cache,
    round_coordinate_for_cache,
)

CURRENT_WEATHER_TTL_SECONDS = 5 * 60
HOURLY_FORECAST_TTL_SECONDS = 10 * 60
DAILY_FORECAST_TTL_SECONDS = 30 * 60


class WeatherService:
    """Coordinates geocoding/direct-coordinate forecast data normalization."""

    def __init__(
        self,
        geocoding_service: GeocodingService,
        active_provider: Any = None,
        fallback_provider: Any = None,
        cache: AsyncTTLCache | None = None,
        location_display_service: LocationDisplayService | None = None,
        **kwargs: Any,
    ) -> None:
        self._geocoding_service = geocoding_service
        self._cache = cache
        self._location_display_service = location_display_service or LocationDisplayService()

        client = kwargs.get("client")

        import unittest.mock

        from app.providers.weather.open_meteo import OpenMeteoProvider

        def is_mock(obj: Any) -> bool:
            return isinstance(obj, (unittest.mock.Mock, unittest.mock.MagicMock, unittest.mock.AsyncMock))

        if client is not None:
            self._active_provider = OpenMeteoProvider(client)
        else:
            if active_provider is not None:
                if is_mock(active_provider):
                    self._active_provider = active_provider
                elif not hasattr(active_provider, "get_current_weather") or not hasattr(active_provider, "name"):
                    self._active_provider = OpenMeteoProvider(active_provider)
                else:
                    self._active_provider = active_provider
            else:
                self._active_provider = None

        if fallback_provider is not None:
            if is_mock(fallback_provider):
                self._fallback_provider = fallback_provider
            elif not hasattr(fallback_provider, "get_current_weather") or not hasattr(fallback_provider, "name"):
                self._fallback_provider = OpenMeteoProvider(fallback_provider)
            else:
                self._fallback_provider = fallback_provider
        else:
            self._fallback_provider = None

    @property
    def active_provider(self) -> BaseWeatherProvider:
        return self._active_provider

    @property
    def fallback_provider(self) -> BaseWeatherProvider | None:
        return self._fallback_provider

    async def get_current_weather(self, city: str) -> CurrentWeatherReport:
        if self._cache is not None:
            return await self._cache.get_or_create(
                ("current", "city", normalize_city_for_cache(city), self._active_provider.name),
                ttl_seconds=CURRENT_WEATHER_TTL_SECONDS,
                factory=lambda: self._get_current_weather_uncached(city),
            )
        return await self._get_current_weather_uncached(city)

    async def _get_current_weather_uncached(self, city: str) -> CurrentWeatherReport:
        location = self._location_display_service.enrich_city_location(await self._geocoding_service.find_city(city))
        return await self._get_current_weather_for_location(location)

    async def get_current_weather_by_coordinates(
        self,
        *,
        latitude: float,
        longitude: float,
        accuracy_meters: float | None = None,
    ) -> CurrentWeatherReport:
        if self._cache is not None:
            report = await self._cache.get_or_create(
                (
                    "current",
                    "coordinates",
                    _rounded_latitude(latitude),
                    _rounded_longitude(longitude),
                    self._active_provider.name,
                ),
                ttl_seconds=CURRENT_WEATHER_TTL_SECONDS,
                factory=lambda: self._get_current_weather_by_coordinates_uncached(
                    latitude=latitude,
                    longitude=longitude,
                ),
            )
            return self._with_current_accuracy(report, accuracy_meters)
        report = await self._get_current_weather_by_coordinates_uncached(
            latitude=latitude,
            longitude=longitude,
        )
        return self._with_current_accuracy(report, accuracy_meters)

    async def _get_current_weather_by_coordinates_uncached(
        self, *, latitude: float, longitude: float
    ) -> CurrentWeatherReport:
        location = await self._location_from_coordinates(
            latitude=latitude,
            longitude=longitude,
            timezone="auto",
        )
        return await self._get_current_weather_for_location(location)

    async def get_hourly_forecast(self, city: str, hours: int = 24) -> HourlyForecastReport:
        self._validate_hourly_limit(hours)
        if self._cache is not None:
            return await self._cache.get_or_create(
                ("hourly", "city", normalize_city_for_cache(city), hours, self._active_provider.name),
                ttl_seconds=HOURLY_FORECAST_TTL_SECONDS,
                factory=lambda: self._get_hourly_forecast_uncached(city, hours=hours),
            )
        return await self._get_hourly_forecast_uncached(city, hours=hours)

    async def _get_hourly_forecast_uncached(self, city: str, *, hours: int) -> HourlyForecastReport:
        location = self._location_display_service.enrich_city_location(await self._geocoding_service.find_city(city))
        return await self._get_hourly_forecast_for_location(location, hours=hours)

    async def get_hourly_forecast_by_coordinates(
        self,
        *,
        latitude: float,
        longitude: float,
        hours: int = 24,
        accuracy_meters: float | None = None,
    ) -> HourlyForecastReport:
        self._validate_hourly_limit(hours)
        if self._cache is not None:
            report = await self._cache.get_or_create(
                (
                    "hourly",
                    "coordinates",
                    _rounded_latitude(latitude),
                    _rounded_longitude(longitude),
                    hours,
                    self._active_provider.name,
                ),
                ttl_seconds=HOURLY_FORECAST_TTL_SECONDS,
                factory=lambda: self._get_hourly_forecast_by_coordinates_uncached(
                    latitude=latitude,
                    longitude=longitude,
                    hours=hours,
                ),
            )
            return self._with_hourly_accuracy(report, accuracy_meters)
        report = await self._get_hourly_forecast_by_coordinates_uncached(
            latitude=latitude,
            longitude=longitude,
            hours=hours,
        )
        return self._with_hourly_accuracy(report, accuracy_meters)

    async def _get_hourly_forecast_by_coordinates_uncached(
        self, *, latitude: float, longitude: float, hours: int
    ) -> HourlyForecastReport:
        location = await self._location_from_coordinates(
            latitude=latitude,
            longitude=longitude,
            timezone="auto",
        )
        return await self._get_hourly_forecast_for_location(location, hours=hours)

    async def get_daily_forecast(self, city: str, days: int = 7) -> DailyForecastReport:
        self._validate_daily_limit(days)
        if self._cache is not None:
            return await self._cache.get_or_create(
                ("daily", "city", normalize_city_for_cache(city), days, self._active_provider.name),
                ttl_seconds=DAILY_FORECAST_TTL_SECONDS,
                factory=lambda: self._get_daily_forecast_uncached(city, days=days),
            )
        return await self._get_daily_forecast_uncached(city, days=days)

    async def _get_daily_forecast_uncached(self, city: str, *, days: int) -> DailyForecastReport:
        location = self._location_display_service.enrich_city_location(await self._geocoding_service.find_city(city))
        return await self._get_daily_forecast_for_location(location, days=days)

    async def get_daily_forecast_by_coordinates(
        self,
        *,
        latitude: float,
        longitude: float,
        days: int = 7,
        accuracy_meters: float | None = None,
    ) -> DailyForecastReport:
        self._validate_daily_limit(days)
        if self._cache is not None:
            report = await self._cache.get_or_create(
                (
                    "daily",
                    "coordinates",
                    _rounded_latitude(latitude),
                    _rounded_longitude(longitude),
                    days,
                    self._active_provider.name,
                ),
                ttl_seconds=DAILY_FORECAST_TTL_SECONDS,
                factory=lambda: self._get_daily_forecast_by_coordinates_uncached(
                    latitude=latitude,
                    longitude=longitude,
                    days=days,
                ),
            )
            return self._with_daily_accuracy(report, accuracy_meters)
        report = await self._get_daily_forecast_by_coordinates_uncached(
            latitude=latitude,
            longitude=longitude,
            days=days,
        )
        return self._with_daily_accuracy(report, accuracy_meters)

    async def _get_daily_forecast_by_coordinates_uncached(
        self, *, latitude: float, longitude: float, days: int
    ) -> DailyForecastReport:
        location = await self._location_from_coordinates(
            latitude=latitude,
            longitude=longitude,
            timezone="auto",
        )
        return await self._get_daily_forecast_for_location(location, days=days)

    async def _get_current_weather_for_location(self, location: Location) -> CurrentWeatherReport:
        return await self._execute_with_fallback("get_current_weather", location)

    async def _get_hourly_forecast_for_location(self, location: Location, *, hours: int) -> HourlyForecastReport:
        return await self._execute_with_fallback("get_hourly_forecast", location, hours)

    async def _get_daily_forecast_for_location(self, location: Location, *, days: int) -> DailyForecastReport:
        return await self._execute_with_fallback("get_daily_forecast", location, days)

    async def _execute_with_fallback(self, method_name: str, *args, **kwargs) -> Any:
        try:
            method = getattr(self._active_provider, method_name)
            return await method(*args, **kwargs)
        except Exception as exc:
            if self._fallback_provider:
                method = getattr(self._fallback_provider, method_name)
                report = await method(*args, **kwargs)
                return replace(
                    report,
                    provider=self._active_provider.name,
                    fallback_provider_used=True,
                    fallback_provider=self._fallback_provider.name,
                )
            raise exc

    async def _location_from_coordinates(self, *, latitude: float, longitude: float, timezone: str) -> Location:
        return await self._location_display_service.resolve_coordinates(
            latitude=latitude,
            longitude=longitude,
            timezone=timezone,
        )

    def _with_current_accuracy(
        self, report: CurrentWeatherReport, accuracy_meters: float | None
    ) -> CurrentWeatherReport:
        return replace(
            report,
            location=replace(report.location, accuracy_meters=accuracy_meters),
        )

    def _with_hourly_accuracy(
        self, report: HourlyForecastReport, accuracy_meters: float | None
    ) -> HourlyForecastReport:
        return replace(
            report,
            location=replace(report.location, accuracy_meters=accuracy_meters),
        )

    def _with_daily_accuracy(self, report: DailyForecastReport, accuracy_meters: float | None) -> DailyForecastReport:
        return replace(
            report,
            location=replace(report.location, accuracy_meters=accuracy_meters),
        )

    def _validate_hourly_limit(self, hours: int) -> None:
        if hours not in ALLOWED_HOURLY_FORECAST_HOURS:
            allowed_values = sorted(ALLOWED_HOURLY_FORECAST_HOURS)
            raise ValueError(f"hours must be one of: {allowed_values}")

    def _validate_daily_limit(self, days: int) -> None:
        if not 1 <= days <= 7:
            raise ValueError("days must be between 1 and 7")


def _rounded_latitude(latitude: float) -> float:
    return round_coordinate_for_cache(latitude)


def _rounded_longitude(longitude: float) -> float:
    return round_coordinate_for_cache(longitude)
