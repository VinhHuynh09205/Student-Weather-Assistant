from unittest.mock import AsyncMock

import pytest

from app.core.config import Settings
from app.models.domain import Location
from app.providers.weather.open_weather import OpenWeatherProvider
from app.services.weather_service import WeatherService


@pytest.fixture
def settings(monkeypatch) -> Settings:
    monkeypatch.setenv("WEATHER_PROVIDER", "openweather")
    monkeypatch.setenv("WEATHER_FALLBACK_PROVIDER", "open_meteo")
    monkeypatch.setenv("OPENWEATHER_API_KEY", "mock_key")
    monkeypatch.setenv("OPENWEATHER_BASE_URL", "https://api.openweathermap.org")
    monkeypatch.setenv("DEBUG_WEATHER_COMPARE", "true")
    from app.core.config import get_settings

    get_settings.cache_clear()
    return get_settings()


@pytest.fixture
def mock_location() -> Location:
    return Location(
        city="Can Tho",
        country="Vietnam",
        latitude=10.0371,
        longitude=105.7882,
        timezone="Asia/Ho_Chi_Minh",
    )


def test_openweather_provider_normalizes_current(settings, mock_location):
    provider = OpenWeatherProvider(settings)

    mock_payload = {
        "dt": 1623000000,
        "main": {
            "temp": 28.5,
            "feels_like": 31.2,
            "humidity": 75,
            "pressure": 1010,
        },
        "wind": {
            "speed": 3.5,
            "deg": 180,
        },
        "weather": [
            {
                "id": 800,
                "description": "trời quang",
            }
        ],
        "sys": {
            "sunrise": 1622970000,
            "sunset": 1623010000,
        },
        "clouds": {
            "all": 10,
        },
        "visibility": 9000,
    }

    report = provider._parse_current(mock_payload, mock_location.timezone)

    assert report.temperature_c == 28.5
    assert report.apparent_temperature_c == 31.2
    assert report.relative_humidity_percent == 75
    assert report.weather_code == 0
    assert report.weather_description == "Trời quang"
    assert report.wind_speed_kmh == 3.5 * 3.6
    assert report.pressure_hpa == 1010.0
    assert report.visibility_meters == 9000.0
    assert report.cloud_cover_percent == 10
    assert report.is_day is True


def test_openweather_provider_normalizes_hourly(settings, mock_location):
    provider = OpenWeatherProvider(settings)

    mock_payload = {
        "list": [
            {
                "dt": 1623000000,
                "main": {"temp": 28.0, "feels_like": 30.5, "humidity": 80},
                "wind": {"speed": 2.0},
                "weather": [{"id": 500, "description": "mưa nhẹ"}],
                "sys": {"pod": "d"},
                "pop": 0.65,
                "rain": {"3h": 1.5},
            }
        ]
    }

    hourly = provider._parse_hourly(mock_payload, limit=1, timezone_str=mock_location.timezone)
    assert len(hourly) == 1
    assert hourly[0].temperature_c == 28.0
    assert hourly[0].apparent_temperature_c == 30.5
    assert hourly[0].relative_humidity_percent == 80
    assert hourly[0].weather_code == 61
    assert hourly[0].precipitation_probability_percent == 65
    assert hourly[0].precipitation_mm == 1.5 / 3.0


def test_openweather_provider_normalizes_daily(settings, mock_location):
    provider = OpenWeatherProvider(settings)

    mock_payload = {
        "list": [
            {
                "dt": 1623000000,
                "main": {"temp": 28.0, "feels_like": 30.5, "humidity": 80},
                "wind": {"speed": 2.0},
                "weather": [{"id": 500, "description": "mưa nhẹ"}],
                "sys": {"pod": "d"},
                "pop": 0.65,
                "rain": {"3h": 1.5},
            }
        ]
    }

    daily = provider._parse_daily(mock_payload, limit=1, timezone_str=mock_location.timezone)
    assert len(daily) == 1
    assert daily[0].weather_code == 61
    assert daily[0].precipitation_probability_max_percent == 65
    assert daily[0].rain_sum_mm == 1.5


def test_openweather_provider_maps_heavy_rain_and_showers(settings):
    provider = OpenWeatherProvider(settings)

    assert provider._parse_current(
        {
            "dt": 1623000000,
            "main": {"temp": 28.0, "feels_like": 31.0, "humidity": 85},
            "wind": {"speed": 3.0},
            "weather": [{"id": 502, "description": "mưa lớn"}],
            "sys": {"sunrise": 1622970000, "sunset": 1623010000},
        },
        "Asia/Ho_Chi_Minh",
    ).weather_code == 65

    assert provider._parse_current(
        {
            "dt": 1623000000,
            "main": {"temp": 28.0, "feels_like": 31.0, "humidity": 85},
            "wind": {"speed": 3.0},
            "weather": [{"id": 522, "description": "mưa rào nặng hạt"}],
            "sys": {"sunrise": 1622970000, "sunset": 1623010000},
        },
        "Asia/Ho_Chi_Minh",
    ).weather_code == 82


@pytest.mark.anyio
async def test_weather_service_uses_openweather_and_fallback(settings, mock_location):
    mock_ow = AsyncMock()
    mock_ow.name = "openweather"
    mock_ow.get_current_weather = AsyncMock(side_effect=Exception("OWM API limit exceeded"))

    mock_om = AsyncMock()
    mock_om.name = "open_meteo"

    from app.models.domain import CurrentWeatherReport, WeatherSnapshot

    dummy_snapshot = WeatherSnapshot(
        time="2026-06-07T12:00",
        temperature_c=25.0,
        apparent_temperature_c=27.0,
        relative_humidity_percent=80,
        precipitation_probability_percent=10,
        precipitation_mm=0.0,
        rain_mm=0.0,
        weather_code=0,
        weather_description="Clear",
        wind_speed_kmh=10.0,
        uv_index=5.0,
        is_day=True,
    )
    dummy_report = CurrentWeatherReport(
        location=mock_location,
        current=dummy_snapshot,
        provider="open_meteo",
    )
    mock_om.get_current_weather = AsyncMock(return_value=dummy_report)

    service = WeatherService(
        geocoding_service=AsyncMock(),
        active_provider=mock_ow,
        fallback_provider=mock_om,
    )

    report = await service.get_current_weather_by_coordinates(latitude=10.0, longitude=106.0)

    mock_ow.get_current_weather.assert_called_once()
    mock_om.get_current_weather.assert_called_once()

    assert report.fallback_provider_used is True
    assert report.fallback_provider == "open_meteo"
