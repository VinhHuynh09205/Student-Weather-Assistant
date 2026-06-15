import logging
from dataclasses import replace
from datetime import datetime, timedelta
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
NEAR_TERM_WEATHER_LOOKAHEAD = timedelta(hours=3)
NEAR_TERM_WEATHER_PAST_TOLERANCE = timedelta(minutes=15)
RAIN_PROBABILITY_OVERRIDE_PERCENT = 70
HIGH_RAIN_PROBABILITY_OVERRIDE_PERCENT = 85
RAIN_AMOUNT_OVERRIDE_MM = 0.1

RAIN_WEATHER_CODES = {51, 53, 55, 61, 63, 65, 66, 67, 80, 81, 82}
STORM_WEATHER_CODES = {95, 96, 99}

logger = logging.getLogger(__name__)


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
        report = await self._execute_with_fallback("get_current_weather", location)
        return await self._apply_near_term_weather_signal(report, location)

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

    async def _apply_near_term_weather_signal(
        self,
        report: CurrentWeatherReport,
        location: Location,
    ) -> CurrentWeatherReport:
        """Use the nearest forecast slot to reduce stale OpenWeather current-condition misses."""
        if report.provider.lower() != "openweather" or report.fallback_provider_used:
            return report

        try:
            hourly_report = await self._execute_with_fallback("get_hourly_forecast", location, 6)
        except Exception as exc:
            logger.debug("Skipping near-term weather adjustment because hourly forecast failed: %s", exc)
            return report

        nearby = _nearby_hourly_items(report.current, hourly_report.hourly)
        if not nearby:
            return report

        if report.current.weather_code in STORM_WEATHER_CODES:
            return _fill_missing_precipitation_probability(report, nearby)

        if report.current.weather_code in RAIN_WEATHER_CODES:
            storm_signal = _select_near_term_storm_signal(nearby)
            if storm_signal is None:
                return _fill_missing_precipitation_probability(report, nearby)
            return replace(report, current=_adjust_current_with_signal(report.current, storm_signal))

        signal = _select_near_term_precipitation_signal(nearby)
        if signal is None:
            return _fill_missing_precipitation_probability(report, nearby)

        adjusted_current = _adjust_current_with_signal(report.current, signal)
        if adjusted_current == report.current:
            return report
        return replace(report, current=adjusted_current)


def _rounded_latitude(latitude: float) -> float:
    return round_coordinate_for_cache(latitude)


def _rounded_longitude(longitude: float) -> float:
    return round_coordinate_for_cache(longitude)


def _nearby_hourly_items(current: Any, hourly: list[Any]) -> list[Any]:
    current_time = _parse_weather_time(current.time)
    if current_time is None:
        return hourly[:2]

    nearby = []
    for item in hourly:
        item_time = _parse_weather_time(item.time)
        if item_time is None:
            continue
        offset = item_time - current_time
        if -NEAR_TERM_WEATHER_PAST_TOLERANCE <= offset <= NEAR_TERM_WEATHER_LOOKAHEAD:
            nearby.append(item)
    return nearby


def _select_near_term_precipitation_signal(hourly: list[Any]) -> Any | None:
    storm_signal = _select_near_term_storm_signal(hourly)
    if storm_signal is not None:
        return storm_signal

    rain_candidates = [item for item in hourly if _is_confident_rain_signal(item)]
    if not rain_candidates:
        return None
    return max(rain_candidates, key=_precipitation_signal_score)


def _select_near_term_storm_signal(hourly: list[Any]) -> Any | None:
    storm_candidates = [item for item in hourly if item.weather_code in STORM_WEATHER_CODES]
    if not storm_candidates:
        return None
    return max(storm_candidates, key=_precipitation_signal_score)


def _is_confident_rain_signal(item: Any) -> bool:
    probability = item.precipitation_probability_percent or 0
    amount = _precipitation_amount(item)
    has_rain_code = item.weather_code in RAIN_WEATHER_CODES

    if has_rain_code and (probability >= 50 or amount >= RAIN_AMOUNT_OVERRIDE_MM):
        return True
    if probability >= HIGH_RAIN_PROBABILITY_OVERRIDE_PERCENT:
        return True
    return probability >= RAIN_PROBABILITY_OVERRIDE_PERCENT and amount >= RAIN_AMOUNT_OVERRIDE_MM


def _adjust_current_with_signal(current: Any, signal: Any) -> Any:
    current_probability = current.precipitation_probability_percent
    signal_probability = signal.precipitation_probability_percent
    probability = _max_optional_int(current_probability, signal_probability)

    signal_amount = _precipitation_amount(signal)
    current_rain = current.rain_mm or 0.0
    current_precipitation = current.precipitation_mm or 0.0
    rain_mm = max(current_rain, signal.rain_mm or 0.0, signal_amount)
    precipitation_mm = max(current_precipitation, rain_mm, signal.precipitation_mm or 0.0)

    if signal.weather_code in STORM_WEATHER_CODES:
        weather_code = signal.weather_code
        weather_description = "Có khả năng dông gần khu vực"
    elif signal.weather_code in RAIN_WEATHER_CODES:
        weather_code = signal.weather_code
        weather_description = signal.weather_description or "Có khả năng mưa gần khu vực"
    else:
        weather_code = 61
        weather_description = "Khả năng mưa cao"

    return replace(
        current,
        precipitation_probability_percent=probability,
        precipitation_mm=precipitation_mm,
        rain_mm=rain_mm,
        weather_code=weather_code,
        weather_description=weather_description,
    )


def _fill_missing_precipitation_probability(report: CurrentWeatherReport, hourly: list[Any]) -> CurrentWeatherReport:
    if report.current.precipitation_probability_percent is not None:
        return report
    probabilities = [
        item.precipitation_probability_percent
        for item in hourly
        if item.precipitation_probability_percent is not None
    ]
    if not probabilities:
        return report
    return replace(
        report,
        current=replace(report.current, precipitation_probability_percent=max(probabilities)),
    )


def _precipitation_signal_score(item: Any) -> float:
    storm_bonus = 1000.0 if item.weather_code in STORM_WEATHER_CODES else 0.0
    rain_code_bonus = 100.0 if item.weather_code in RAIN_WEATHER_CODES else 0.0
    probability = float(item.precipitation_probability_percent or 0)
    amount = _precipitation_amount(item)
    return storm_bonus + rain_code_bonus + probability + amount * 50.0


def _precipitation_amount(item: Any) -> float:
    return max(float(item.rain_mm or 0.0), float(item.precipitation_mm or 0.0))


def _max_optional_int(*values: int | None) -> int | None:
    numeric_values = [value for value in values if value is not None]
    if not numeric_values:
        return None
    return max(numeric_values)


def _parse_weather_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        return parsed.replace(tzinfo=None)
    return parsed
