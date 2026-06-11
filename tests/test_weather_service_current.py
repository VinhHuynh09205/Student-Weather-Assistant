import asyncio
from typing import Any

from app.models.domain import Location
from app.services.weather_service import WeatherService


class FakeGeocodingService:
    async def find_city(self, city: str) -> Location:
        return Location(
            city=city,
            country="Vietnam",
            latitude=10.0,
            longitude=106.0,
            timezone="Asia/Ho_Chi_Minh",
        )


class FakeForecastClient:
    async def get_forecast(
        self,
        *,
        latitude: float,
        longitude: float,
        timezone: str,
        forecast_days: int,
    ) -> dict[str, Any]:
        return {
            "timezone": "Asia/Ho_Chi_Minh",
            "current": {
                "time": "2026-06-06T21:00",
                "temperature_2m": 28.0,
                "apparent_temperature": 31.0,
                "relative_humidity_2m": 80,
                "precipitation": 0.0,
                "rain": 0.0,
                "weather_code": 2,
                "wind_speed_10m": 8.0,
                "is_day": 0,
            },
            "hourly": {
                "time": ["2026-06-06T21:00"],
                "temperature_2m": [28.0],
                "apparent_temperature": [31.0],
                "relative_humidity_2m": [80],
                "precipitation_probability": [16],
                "precipitation": [0.0],
                "rain": [0.0],
                "weather_code": [2],
                "wind_speed_10m": [8.0],
                "uv_index": [11.0],
                "is_day": [0],
            },
            "daily": {
                "time": ["2026-06-06"],
                "weather_code": [2],
                "temperature_2m_max": [31.0],
                "temperature_2m_min": [25.0],
                "precipitation_probability_max": [20],
                "rain_sum": [0.0],
                "wind_speed_10m_max": [10.0],
                "uv_index_max": [11.0],
                "sunrise": ["2026-06-06T05:30"],
                "sunset": ["2026-06-06T18:15"],
            },
        }


def test_current_weather_uses_current_night_uv_and_hourly_rain_probability() -> None:
    async def scenario() -> None:
        service = WeatherService(
            FakeGeocodingService(),  # type: ignore[arg-type]
            FakeForecastClient(),  # type: ignore[arg-type]
        )

        report = await service.get_current_weather_by_coordinates(
            latitude=10.3759,
            longitude=106.3439,
        )

        assert report.current.is_day is False
        assert report.current.uv_index == 0.0
        assert report.current.precipitation_probability_percent == 16
        assert report.current.rain_mm == 0.0

    asyncio.run(scenario())
