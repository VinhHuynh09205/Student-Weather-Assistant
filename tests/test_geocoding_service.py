import asyncio
from typing import Any

import pytest

from app.core.exceptions import CityNotFoundError
from app.services.geocoding_service import GeocodingService


@pytest.fixture(autouse=True)
def mock_openweather_geocode(monkeypatch):
    async def mock_geocode(*args, **kwargs):
        return []

    from app.providers.location.openweather import OpenWeatherGeocodingProvider

    monkeypatch.setattr(OpenWeatherGeocodingProvider, "geocode", mock_geocode)


class FakeOpenMeteoClient:
    def __init__(self, responses: dict[str, dict[str, Any]] | None = None) -> None:
        self.responses = responses or {}
        self.calls: list[tuple[str, int, str]] = []

    async def search_city(self, city: str, *, count: int = 10, language: str = "en") -> dict[str, Any]:
        self.calls.append((city, count, language))
        return self.responses.get(city, {"results": []})


def test_find_city_uses_fallback_when_geocoding_has_no_ba_ria_result() -> None:
    client = FakeOpenMeteoClient()
    service = GeocodingService(client)  # type: ignore[arg-type]

    location = asyncio.run(service.find_city("bà rịa vũng tàu"))

    assert location.city == "Bà Rịa - Vũng Tàu"
    assert location.country == "Vietnam"
    assert location.latitude == 10.5417
    assert location.longitude == 107.2429
    assert ("bà rịa vũng tàu", 10, "en") in client.calls
    assert ("ba ria vung tau", 10, "en") in client.calls


def test_find_city_prefers_vietnam_result_when_provider_returns_many_results() -> None:
    client = FakeOpenMeteoClient(
        {
            "hue": {
                "results": [
                    {
                        "name": "Hue",
                        "country": "United States",
                        "country_code": "US",
                        "latitude": 40.0,
                        "longitude": -90.0,
                        "timezone": "America/Chicago",
                    },
                    {
                        "name": "Hue",
                        "country": "Vietnam",
                        "country_code": "VN",
                        "latitude": 16.4637,
                        "longitude": 107.5909,
                        "timezone": "Asia/Ho_Chi_Minh",
                    },
                ]
            }
        }
    )
    service = GeocodingService(client)  # type: ignore[arg-type]

    location = asyncio.run(service.find_city("hue"))

    assert location.country == "Vietnam"
    assert location.latitude == 16.4637
    assert location.longitude == 107.5909


def test_find_city_uses_vietnamese_display_name_for_known_alias() -> None:
    client = FakeOpenMeteoClient(
        {
            "Can Tho": {
                "results": [
                    {
                        "name": "Can Tho",
                        "country": "Vietnam",
                        "country_code": "VN",
                        "latitude": 10.0452,
                        "longitude": 105.7469,
                        "timezone": "Asia/Ho_Chi_Minh",
                    }
                ]
            }
        }
    )
    service = GeocodingService(client)  # type: ignore[arg-type]

    location = asyncio.run(service.find_city("Can Tho"))

    assert location.city == "C\u1ea7n Th\u01a1"
    assert location.country == "Vietnam"
    assert location.latitude == 10.0452
    assert location.longitude == 105.7469


def test_find_city_raises_not_found_when_no_result_or_fallback_exists() -> None:
    client = FakeOpenMeteoClient()
    service = GeocodingService(client)  # type: ignore[arg-type]

    with pytest.raises(CityNotFoundError):
        asyncio.run(service.find_city("abcxyz123notacity"))
