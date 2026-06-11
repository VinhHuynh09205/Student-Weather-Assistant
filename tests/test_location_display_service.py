import asyncio
from unittest.mock import ANY, AsyncMock

from app.services.location_display_service import LocationDisplayService
from app.services.weather_service import WeatherService
from app.utils.location_normalizer import normalize_location_key


def test_coordinate_location_display_uses_nearest_vietnam_location() -> None:
    service = LocationDisplayService()
    # Mock geocoding to return a successful match
    service._query_reverse_geocoding = AsyncMock(return_value=("Trung An", "Tiền Giang", ["Trung An", "Tiền Giang"]))

    location = asyncio.run(
        service.resolve_coordinates(
            latitude=10.3759,
            longitude=106.3439,
            timezone="Asia/Ho_Chi_Minh",
            accuracy_meters=108,
        )
    )

    assert location.source == "coordinates"
    assert normalize_location_key(location.city) == "tien giang"
    assert "ho chi minh" not in normalize_location_key(location.display_name or "")
    assert location.accuracy_meters == 108
    assert location.display_name == "Trung An, Tiền Giang"
    assert location.location_confidence == "district"


def test_coordinate_location_display_falls_back_to_rounded_coordinates() -> None:
    service = LocationDisplayService()
    # Mock geocoding to return empty (failed API)
    service._query_reverse_geocoding = AsyncMock(return_value=(None, None, []))

    location = asyncio.run(
        service.resolve_coordinates(
            latitude=-20.123456,
            longitude=-130.987654,
            timezone="auto",
        )
    )

    assert location.source == "coordinates"
    assert normalize_location_key(location.city) == "vi tri hien tai"
    assert location.display_name == "Vị trí hiện tại chưa xác định rõ"
    assert location.location_confidence == "coordinates"
    assert location.needs_user_confirmation is True


def test_gps_tiengiang_longtien_never_returns_vinhlong_or_bentre() -> None:
    # Scenario A: API failed/mismatched. Must fallback to coordinates (uncertain), NOT Vĩnh Long or Bến Tre.
    service_a = LocationDisplayService()
    service_a._query_reverse_geocoding = AsyncMock(return_value=(None, None, []))
    location = asyncio.run(
        service_a.resolve_coordinates(
            latitude=10.3502,
            longitude=106.1406,
            timezone="Asia/Ho_Chi_Minh",
        )
    )
    assert location.location_confidence == "uncertain"
    assert "vinh long" not in normalize_location_key(location.display_name or "")
    assert "ben tre" not in normalize_location_key(location.display_name or "")
    assert location.display_name == "Vị trí hiện tại chưa xác định rõ"
    assert location.needs_user_confirmation is True

    # Scenario B: API returned Tien Giang in informative list. Must return Tien Giang.
    service_b = LocationDisplayService()
    service_b._query_reverse_geocoding = AsyncMock(
        return_value=("Long Tiên", "Đồng Tháp", ["Đồng Tháp", "Tiền Giang", "Long Tiên"])
    )
    location = asyncio.run(
        service_b.resolve_coordinates(
            latitude=10.3502,
            longitude=106.1406,
            timezone="Asia/Ho_Chi_Minh",
        )
    )
    assert normalize_location_key(location.city) == "tien giang"
    assert location.location_confidence == "district"
    assert "Long Tiên, Tiền Giang" in (location.display_name or "")


def test_gps_tiengiang_trungan_never_returns_vinhlong_or_bentre() -> None:
    # Scenario A: API failed/mismatched. Must fallback to coordinates (uncertain).
    service_a = LocationDisplayService()
    service_a._query_reverse_geocoding = AsyncMock(return_value=(None, None, []))
    location = asyncio.run(
        service_a.resolve_coordinates(
            latitude=10.3759,
            longitude=106.3439,
            timezone="Asia/Ho_Chi_Minh",
        )
    )
    assert location.location_confidence == "uncertain"
    assert "vinh long" not in normalize_location_key(location.display_name or "")
    assert "ben tre" not in normalize_location_key(location.display_name or "")
    assert location.display_name == "Vị trí hiện tại chưa xác định rõ"
    assert location.needs_user_confirmation is True

    # Scenario B: API returned Tien Giang in informative list. Must return Tien Giang.
    service_b = LocationDisplayService()
    service_b._query_reverse_geocoding = AsyncMock(
        return_value=("Trung An", "Đồng Tháp", ["Đồng Tháp", "Tiền Giang", "Trung An"])
    )
    location = asyncio.run(
        service_b.resolve_coordinates(
            latitude=10.3759,
            longitude=106.3439,
            timezone="Asia/Ho_Chi_Minh",
        )
    )
    assert normalize_location_key(location.city) == "tien giang"
    assert location.location_confidence == "district"
    assert "Trung An, Tiền Giang" in (location.display_name or "")


def test_weather_by_coordinates_does_not_call_city_geocoding() -> None:
    async def scenario() -> None:
        mock_geocoding = AsyncMock()
        mock_client = AsyncMock()
        mock_location_display = LocationDisplayService()
        mock_location_display._query_reverse_geocoding = AsyncMock(return_value=(None, None, []))

        # Mock get_forecast to return a valid weather payload
        mock_client.get_forecast = AsyncMock(
            return_value={
                "timezone": "Asia/Ho_Chi_Minh",
                "current": {
                    "time": "2026-06-05T10:00",
                    "weather_code": 0,
                    "temperature_2m": 25.0,
                    "apparent_temperature": 27.0,
                    "relative_humidity_2m": 80,
                    "precipitation": 0.0,
                    "rain": 0.0,
                    "wind_speed_10m": 10.0,
                    "is_day": 1,
                },
                "hourly": {
                    "time": ["2026-06-05T10:00"],
                    "temperature_2m": [25.0],
                    "apparent_temperature": [27.0],
                    "relative_humidity_2m": [80],
                    "precipitation_probability": [10],
                    "precipitation": [0.0],
                    "rain": [0.0],
                    "weather_code": [0],
                    "wind_speed_10m": [10.0],
                    "uv_index": [5.0],
                    "is_day": [1],
                },
            }
        )

        service = WeatherService(
            geocoding_service=mock_geocoding,
            client=mock_client,
            location_display_service=mock_location_display,
        )

        report = await service.get_current_weather_by_coordinates(
            latitude=10.3502,
            longitude=106.1406,
        )

        # Verify geocoding city was not called
        mock_geocoding.find_city.assert_not_called()
        # Verify forecast was called with actual coordinates and 3 forecast days (FORECAST_DAYS_FOR_HOURLY)
        mock_client.get_forecast.assert_called_once_with(
            latitude=10.3502,
            longitude=106.1406,
            timezone=ANY,
            forecast_days=3,
        )
        # Verify weather reports still uses the original coordinates, not display name
        assert report.location.latitude == 10.3502
        assert report.location.longitude == 106.1406

    asyncio.run(scenario())
