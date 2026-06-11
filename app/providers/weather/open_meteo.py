from typing import Any

from app.clients.open_meteo_client import OpenMeteoClient
from app.core.constants import FORECAST_DAYS_FOR_HOURLY
from app.core.exceptions import InvalidWeatherDataError
from app.models.domain import (
    CurrentWeatherReport,
    DailyForecast,
    DailyForecastReport,
    HourlyForecastReport,
    Location,
    WeatherSnapshot,
)
from app.providers.weather.base import BaseWeatherProvider
from app.utils.time_utils import parse_open_meteo_time
from app.utils.weather_code_mapper import map_weather_code


class OpenMeteoProvider(BaseWeatherProvider):
    def __init__(self, client: OpenMeteoClient) -> None:
        self._client = client

    @property
    def name(self) -> str:
        return "open_meteo"

    async def get_current_weather(self, location: Location) -> CurrentWeatherReport:
        forecast_data = await self._client.get_forecast(
            latitude=location.latitude,
            longitude=location.longitude,
            timezone=location.timezone,
            forecast_days=FORECAST_DAYS_FOR_HOURLY,
        )
        return CurrentWeatherReport(
            location=location,
            current=self._parse_current_weather(forecast_data),
            provider=self.name,
        )

    async def get_hourly_forecast(self, location: Location, hours: int) -> HourlyForecastReport:
        forecast_data = await self._client.get_forecast(
            latitude=location.latitude,
            longitude=location.longitude,
            timezone=location.timezone,
            forecast_days=FORECAST_DAYS_FOR_HOURLY,
        )
        return HourlyForecastReport(
            location=location,
            hourly=self._parse_hourly_weather(
                forecast_data,
                limit=hours,
                start_time=self._get_current_time(forecast_data),
            ),
            provider=self.name,
        )

    async def get_daily_forecast(self, location: Location, days: int) -> DailyForecastReport:
        forecast_data = await self._client.get_forecast(
            latitude=location.latitude,
            longitude=location.longitude,
            timezone=location.timezone,
            forecast_days=days,
        )
        return DailyForecastReport(
            location=location,
            daily=self._parse_daily_weather(forecast_data, limit=days),
            provider=self.name,
        )

    def _parse_current_weather(self, forecast_data: dict[str, Any]) -> WeatherSnapshot:
        current_data = self._require_mapping(forecast_data, "current")
        current_time = str(self._require_value(current_data, "time"))
        weather_code = self._as_int(self._require_value(current_data, "weather_code"))
        is_day = self._as_bool_or_none(current_data.get("is_day"))
        if is_day is None:
            is_day = self._find_optional_hourly_bool(forecast_data, "is_day", current_time)
        uv_index = self._find_optional_hourly_value(forecast_data, "uv_index", current_time)

        return WeatherSnapshot(
            time=current_time,
            temperature_c=self._as_float(self._require_value(current_data, "temperature_2m")),
            apparent_temperature_c=self._as_float(self._require_value(current_data, "apparent_temperature")),
            relative_humidity_percent=self._as_int(self._require_value(current_data, "relative_humidity_2m")),
            precipitation_probability_percent=self._as_optional_int(
                self._find_optional_hourly_value(forecast_data, "precipitation_probability", current_time)
            ),
            precipitation_mm=self._as_float(self._require_value(current_data, "precipitation")),
            rain_mm=self._as_float(self._require_value(current_data, "rain")),
            weather_code=weather_code,
            weather_description=map_weather_code(weather_code),
            wind_speed_kmh=self._as_float(self._require_value(current_data, "wind_speed_10m")),
            uv_index=0.0 if is_day is False else self._as_float(uv_index or 0),
            is_day=is_day,
            showers_mm=self._as_optional_float(current_data.get("showers")),
            wind_direction_degrees=self._as_optional_int(current_data.get("wind_direction_10m")),
            pressure_hpa=self._as_optional_float(current_data.get("surface_pressure")),
            visibility_meters=self._as_optional_float(current_data.get("visibility")),
            cloud_cover_percent=self._as_optional_int(current_data.get("cloud_cover")),
        )

    def _parse_hourly_weather(
        self,
        forecast_data: dict[str, Any],
        *,
        limit: int,
        start_time: str | None,
    ) -> list[WeatherSnapshot]:
        hourly_data = self._require_mapping(forecast_data, "hourly")
        times = self._require_list(hourly_data, "time")
        start_index = self._find_start_index(times, start_time)
        end_index = min(len(times), start_index + limit)

        forecasts = [self._parse_hourly_item(hourly_data, index) for index in range(start_index, end_index)]
        if not forecasts:
            raise InvalidWeatherDataError("Hourly forecast data is empty.")
        return forecasts

    def _parse_hourly_item(self, hourly_data: dict[str, Any], index: int) -> WeatherSnapshot:
        weather_code = self._as_int(self._get_list_item(hourly_data, "weather_code", index))
        return WeatherSnapshot(
            time=str(self._get_list_item(hourly_data, "time", index)),
            temperature_c=self._as_float(self._get_list_item(hourly_data, "temperature_2m", index)),
            apparent_temperature_c=self._as_float(
                self._get_list_item(hourly_data, "apparent_temperature", index),
            ),
            relative_humidity_percent=self._as_int(self._get_list_item(hourly_data, "relative_humidity_2m", index)),
            precipitation_probability_percent=self._as_int(
                self._get_list_item(hourly_data, "precipitation_probability", index),
            ),
            precipitation_mm=self._as_float(self._get_list_item(hourly_data, "precipitation", index)),
            rain_mm=self._as_float(self._get_list_item(hourly_data, "rain", index)),
            weather_code=weather_code,
            weather_description=map_weather_code(weather_code),
            wind_speed_kmh=self._as_float(self._get_list_item(hourly_data, "wind_speed_10m", index)),
            uv_index=self._as_float(self._get_list_item(hourly_data, "uv_index", index)),
            is_day=self._as_bool_or_none(self._get_optional_list_item(hourly_data, "is_day", index)),
        )

    def _parse_daily_weather(self, forecast_data: dict[str, Any], *, limit: int) -> list[DailyForecast]:
        daily_data = self._require_mapping(forecast_data, "daily")
        times = self._require_list(daily_data, "time")
        end_index = min(len(times), limit)
        forecasts = [self._parse_daily_item(daily_data, index) for index in range(end_index)]
        if not forecasts:
            raise InvalidWeatherDataError("Daily forecast data is empty.")
        return forecasts

    def _parse_daily_item(self, daily_data: dict[str, Any], index: int) -> DailyForecast:
        weather_code = self._as_int(self._get_list_item(daily_data, "weather_code", index))
        return DailyForecast(
            date=str(self._get_list_item(daily_data, "time", index)),
            weather_code=weather_code,
            weather_description=map_weather_code(weather_code),
            temperature_max_c=self._as_float(self._get_list_item(daily_data, "temperature_2m_max", index)),
            temperature_min_c=self._as_float(self._get_list_item(daily_data, "temperature_2m_min", index)),
            precipitation_probability_max_percent=self._as_int(
                self._get_list_item(daily_data, "precipitation_probability_max", index)
            ),
            rain_sum_mm=self._as_float(self._get_list_item(daily_data, "rain_sum", index)),
            wind_speed_max_kmh=self._as_float(self._get_list_item(daily_data, "wind_speed_10m_max", index)),
            uv_index_max=self._as_float(self._get_list_item(daily_data, "uv_index_max", index)),
            sunrise=str(self._get_list_item(daily_data, "sunrise", index)),
            sunset=str(self._get_list_item(daily_data, "sunset", index)),
        )

    def _get_current_time(self, forecast_data: dict[str, Any]) -> str | None:
        current_data = forecast_data.get("current")
        if not isinstance(current_data, dict):
            return None
        current_time = current_data.get("time")
        return str(current_time) if current_time is not None else None

    def _find_optional_hourly_value(self, forecast_data: dict[str, Any], field_name: str, target_time: str) -> Any:
        hourly_data = forecast_data.get("hourly")
        if not isinstance(hourly_data, dict):
            return None
        times = hourly_data.get("time")
        if not isinstance(times, list) or not times:
            return None
        index = self._find_start_index(times, target_time)
        return self._get_optional_list_item(hourly_data, field_name, index)

    def _find_optional_hourly_bool(
        self, forecast_data: dict[str, Any], field_name: str, target_time: str
    ) -> bool | None:
        hourly_data = self._require_mapping(forecast_data, "hourly")
        times = self._require_list(hourly_data, "time")
        index = self._find_start_index(times, target_time)
        return self._as_bool_or_none(self._get_optional_list_item(hourly_data, field_name, index))

    def _find_start_index(self, times: list[Any], start_time: str | None) -> int:
        if start_time is None:
            return 0

        target = parse_open_meteo_time(start_time)
        for index, value in enumerate(times):
            item_time = parse_open_meteo_time(str(value))
            if item_time >= target:
                return index
        return 0

    def _require_mapping(self, data: dict[str, Any], field_name: str) -> dict[str, Any]:
        value = data.get(field_name)
        if not isinstance(value, dict):
            raise InvalidWeatherDataError(f"Forecast response misses '{field_name}'.")
        return value

    def _require_list(self, data: dict[str, Any], field_name: str) -> list[Any]:
        value = data.get(field_name)
        if not isinstance(value, list) or not value:
            raise InvalidWeatherDataError(f"Forecast response misses '{field_name}'.")
        return value

    def _get_list_item(self, data: dict[str, Any], field_name: str, index: int) -> Any:
        values = self._require_list(data, field_name)
        try:
            return values[index]
        except IndexError as exc:
            raise InvalidWeatherDataError(f"Forecast field '{field_name}' is shorter than expected.") from exc

    def _get_optional_list_item(self, data: dict[str, Any], field_name: str, index: int) -> Any:
        values = data.get(field_name)
        if not isinstance(values, list):
            return None
        try:
            return values[index]
        except IndexError:
            return None

    def _require_value(self, data: dict[str, Any], field_name: str) -> Any:
        value = data.get(field_name)
        if value is None:
            raise InvalidWeatherDataError(f"Forecast response misses '{field_name}'.")
        return value

    def _as_float(self, value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError) as exc:
            raise InvalidWeatherDataError("Forecast response contains a non-numeric value.") from exc

    def _as_optional_float(self, value: Any) -> float | None:
        if value is None:
            return None
        return self._as_float(value)

    def _as_int(self, value: Any) -> int:
        try:
            return int(round(float(value)))
        except (TypeError, ValueError) as exc:
            raise InvalidWeatherDataError("Forecast response contains a non-integer value.") from exc

    def _as_optional_int(self, value: Any) -> int | None:
        if value is None:
            return None
        return self._as_int(value)

    def _as_bool_or_none(self, value: Any) -> bool | None:
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        try:
            return bool(int(value))
        except (TypeError, ValueError) as exc:
            raise InvalidWeatherDataError("Forecast response contains an invalid is_day value.") from exc
