import asyncio
from typing import Any

from app.models.domain import CurrentWeatherReport, HourlyForecastReport, Location, WeatherSnapshot
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


class FakeLocationDisplayService:
    async def resolve_coordinates(self, *, latitude: float, longitude: float, timezone: str) -> Location:
        return Location(
            city="Long Trung",
            country="Vietnam",
            latitude=latitude,
            longitude=longitude,
            timezone="Asia/Ho_Chi_Minh",
        )


class CloudyCurrentRainyNearTermProvider:
    name = "openweather"

    async def get_current_weather(self, location: Location) -> CurrentWeatherReport:
        return CurrentWeatherReport(
            location=location,
            current=WeatherSnapshot(
                time="2026-06-13T18:30",
                temperature_c=28.0,
                apparent_temperature_c=32.0,
                relative_humidity_percent=84,
                precipitation_probability_percent=None,
                precipitation_mm=0.0,
                rain_mm=0.0,
                weather_code=3,
                weather_description="Mây đen u ám",
                wind_speed_kmh=12.0,
                uv_index=0.0,
                is_day=False,
                cloud_cover_percent=100,
            ),
            provider=self.name,
        )

    async def get_hourly_forecast(self, location: Location, hours: int) -> HourlyForecastReport:
        return HourlyForecastReport(
            location=location,
            hourly=[
                WeatherSnapshot(
                    time="2026-06-13T19:00",
                    temperature_c=28.0,
                    apparent_temperature_c=32.0,
                    relative_humidity_percent=86,
                    precipitation_probability_percent=99,
                    precipitation_mm=0.3,
                    rain_mm=0.3,
                    weather_code=61,
                    weather_description="Mưa nhẹ",
                    wind_speed_kmh=14.0,
                    uv_index=0.0,
                    is_day=False,
                )
            ],
            provider=self.name,
        )

    async def get_daily_forecast(self, location: Location, days: int):
        raise AssertionError("Daily forecast is not needed for current weather.")


class CloudyCurrentLowConfidenceRainProvider(CloudyCurrentRainyNearTermProvider):
    async def get_hourly_forecast(self, location: Location, hours: int) -> HourlyForecastReport:
        return HourlyForecastReport(
            location=location,
            hourly=[
                WeatherSnapshot(
                    time="2026-06-13T19:00",
                    temperature_c=28.0,
                    apparent_temperature_c=32.0,
                    relative_humidity_percent=86,
                    precipitation_probability_percent=55,
                    precipitation_mm=0.0,
                    rain_mm=0.0,
                    weather_code=3,
                    weather_description="Nhiều mây",
                    wind_speed_kmh=14.0,
                    uv_index=0.0,
                    is_day=False,
                )
            ],
            provider=self.name,
        )


def test_current_weather_uses_near_term_rain_when_openweather_current_lags() -> None:
    async def scenario() -> None:
        service = WeatherService(
            FakeGeocodingService(),  # type: ignore[arg-type]
            active_provider=CloudyCurrentRainyNearTermProvider(),
            location_display_service=FakeLocationDisplayService(),  # type: ignore[arg-type]
        )

        report = await service.get_current_weather_by_coordinates(latitude=10.3419, longitude=106.1223)

        assert report.current.weather_code == 61
        assert report.current.weather_description == "Mưa nhẹ"
        assert report.current.precipitation_probability_percent == 99
        assert report.current.rain_mm == 0.3

    asyncio.run(scenario())


def test_current_weather_does_not_override_clouds_for_weak_near_term_signal() -> None:
    async def scenario() -> None:
        service = WeatherService(
            FakeGeocodingService(),  # type: ignore[arg-type]
            active_provider=CloudyCurrentLowConfidenceRainProvider(),
            location_display_service=FakeLocationDisplayService(),  # type: ignore[arg-type]
        )

        report = await service.get_current_weather_by_coordinates(latitude=10.3419, longitude=106.1223)

        assert report.current.weather_code == 3
        assert report.current.weather_description == "Mây đen u ám"
        assert report.current.precipitation_probability_percent == 55
        assert report.current.rain_mm == 0.0

    asyncio.run(scenario())
