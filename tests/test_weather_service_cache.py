import asyncio
from datetime import datetime, timedelta
from typing import Any

from app.core.constants import FORECAST_DAYS_FOR_HOURLY
from app.models.domain import Location
from app.schemas.advice import StudentAdviceRequest
from app.services.student_advice_service import StudentAdviceService
from app.services.weather_cache import AsyncTTLCache
from app.services.weather_service import WeatherService


class FakeGeocodingService:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def find_city(self, city: str) -> Location:
        self.calls.append(city)
        return Location(
            city=city,
            country="Vietnam",
            latitude=10.0371,
            longitude=105.7883,
            timezone="Asia/Ho_Chi_Minh",
        )


class CountingOpenMeteoClient:
    def __init__(self) -> None:
        self.calls: list[tuple[float, float, str, int]] = []

    async def get_forecast(
        self,
        *,
        latitude: float,
        longitude: float,
        timezone: str,
        forecast_days: int,
    ) -> dict[str, Any]:
        self.calls.append((latitude, longitude, timezone, forecast_days))
        return make_forecast_data(forecast_days=forecast_days)


def make_service() -> tuple[WeatherService, CountingOpenMeteoClient]:
    client = CountingOpenMeteoClient()
    service = WeatherService(
        FakeGeocodingService(),  # type: ignore[arg-type]
        client,  # type: ignore[arg-type]
        cache=AsyncTTLCache(),
    )
    return service, client


def test_current_weather_uses_cache_within_ttl() -> None:
    async def scenario() -> None:
        service, client = make_service()

        await service.get_current_weather("Can Tho")
        await service.get_current_weather("Can Tho")

        assert len(client.calls) == 1

    asyncio.run(scenario())


def test_hourly_forecast_uses_cache_within_ttl() -> None:
    async def scenario() -> None:
        service, client = make_service()

        await service.get_hourly_forecast("Can Tho", hours=24)
        await service.get_hourly_forecast("Can Tho", hours=24)

        assert len(client.calls) == 1

    asyncio.run(scenario())


def test_daily_forecast_uses_cache_within_ttl() -> None:
    async def scenario() -> None:
        service, client = make_service()

        await service.get_daily_forecast("Can Tho", days=7)
        await service.get_daily_forecast("Can Tho", days=7)

        assert len(client.calls) == 1

    asyncio.run(scenario())


def test_coordinate_cache_key_rounds_nearby_gps_values() -> None:
    async def scenario() -> None:
        service, client = make_service()

        await service.get_current_weather_by_coordinates(
            latitude=10.123456,
            longitude=106.123456,
        )
        await service.get_current_weather_by_coordinates(
            latitude=10.123459,
            longitude=106.123459,
        )

        assert len(client.calls) == 1

    asyncio.run(scenario())


def test_student_advice_cache_does_not_replace_current_weather_cache() -> None:
    async def scenario() -> None:
        weather_service, client = make_service()
        advice_service = StudentAdviceService(weather_service, cache=AsyncTTLCache())
        request = StudentAdviceRequest(
            city="Can Tho",
            study_date="2026-06-06",
            start_time="07:30",
            end_time="11:00",
            vehicle_type="motorbike",
        )

        await advice_service.get_student_advice(request)
        await weather_service.get_current_weather("Can Tho")

        assert len(client.calls) == 2
        assert client.calls[0][3] == FORECAST_DAYS_FOR_HOURLY
        assert client.calls[1][3] == FORECAST_DAYS_FOR_HOURLY

    asyncio.run(scenario())


def make_forecast_data(*, forecast_days: int) -> dict[str, Any]:
    start_at = datetime(2026, 6, 6, 7)
    hourly_count = max(72, forecast_days * 24)
    hourly_times = [(start_at + timedelta(hours=offset)).strftime("%Y-%m-%dT%H:%M") for offset in range(hourly_count)]
    daily_dates = [(start_at + timedelta(days=offset)).date().isoformat() for offset in range(forecast_days)]

    return {
        "timezone": "Asia/Ho_Chi_Minh",
        "current": {
            "time": hourly_times[0],
            "temperature_2m": 30.0,
            "apparent_temperature": 34.0,
            "relative_humidity_2m": 76,
            "precipitation": 0.0,
            "rain": 0.0,
            "weather_code": 2,
            "wind_speed_10m": 12.0,
            "is_day": 1,
        },
        "hourly": {
            "time": hourly_times,
            "temperature_2m": [30.0] * hourly_count,
            "apparent_temperature": [34.0] * hourly_count,
            "relative_humidity_2m": [76] * hourly_count,
            "precipitation_probability": [20] * hourly_count,
            "precipitation": [0.0] * hourly_count,
            "rain": [0.0] * hourly_count,
            "weather_code": [2] * hourly_count,
            "wind_speed_10m": [12.0] * hourly_count,
            "uv_index": [5.0] * hourly_count,
            "is_day": [1] * hourly_count,
        },
        "daily": {
            "time": daily_dates,
            "weather_code": [2] * forecast_days,
            "temperature_2m_max": [32.0] * forecast_days,
            "temperature_2m_min": [25.0] * forecast_days,
            "precipitation_probability_max": [30] * forecast_days,
            "rain_sum": [0.2] * forecast_days,
            "wind_speed_10m_max": [16.0] * forecast_days,
            "uv_index_max": [7.0] * forecast_days,
            "sunrise": [f"{date}T05:35" for date in daily_dates],
            "sunset": [f"{date}T18:15" for date in daily_dates],
        },
    }
