import asyncio
from unittest.mock import AsyncMock, MagicMock

from app.services.geocoding_service import GeocodingService
from app.services.location_display_service import LocationDisplayService


def test_resolve_coordinates_exact_confidence() -> None:
    service = LocationDisplayService()
    # Mock reverse geocoding to return exact details: ward_or_commune, district, province
    admin_levels = {
        "hamlet": None,
        "ward_or_commune": "Long Tiên",
        "district": "Cai Lậy",
        "province": "Tiền Giang",
        "country": "Vietnam",
    }
    service._query_reverse_geocoding = AsyncMock(
        return_value=("Long Tiên", "Tiền Giang", ["Long Tiên", "Tiền Giang"], admin_levels, "nominatim")
    )

    # Cai Lay, Tien Giang coordinates
    location = asyncio.run(
        service.resolve_coordinates(latitude=10.3502, longitude=106.1406, timezone="Asia/Ho_Chi_Minh")
    )

    assert location.location_confidence == "exact"
    assert location.needs_user_confirmation is False
    assert location.display_name == "Long Tiên, Cai Lậy, Tiền Giang"
    assert location.short_display_name == "Long Tiên, Tiền Giang"
    assert location.administrative_levels == admin_levels


def test_resolve_coordinates_province_only_confidence() -> None:
    service = LocationDisplayService()
    admin_levels = {
        "hamlet": None,
        "ward_or_commune": None,
        "district": None,
        "province": "Tiền Giang",
        "country": "Vietnam",
    }
    service._query_reverse_geocoding = AsyncMock(
        return_value=("Tiền Giang", "Tiền Giang", ["Tiền Giang"], admin_levels, "nominatim")
    )

    location = asyncio.run(
        service.resolve_coordinates(latitude=10.3502, longitude=106.1406, timezone="Asia/Ho_Chi_Minh")
    )

    assert location.location_confidence == "province"
    assert location.needs_user_confirmation is True
    assert location.display_name == "Tiền Giang"
    assert location.short_display_name == "Tiền Giang"


def test_resolve_coordinates_province_mismatch_uncertain() -> None:
    service = LocationDisplayService()
    # Fallback province for (10.3502, 106.1406) is Tiền Giang.
    # If the API returns Vĩnh Long, it is a mismatch.
    admin_levels = {
        "hamlet": None,
        "ward_or_commune": None,
        "district": None,
        "province": "Vĩnh Long",
        "country": "Vietnam",
    }
    service._query_reverse_geocoding = AsyncMock(
        return_value=("Vĩnh Long", "Vĩnh Long", ["Vĩnh Long"], admin_levels, "nominatim")
    )

    location = asyncio.run(
        service.resolve_coordinates(latitude=10.3502, longitude=106.1406, timezone="Asia/Ho_Chi_Minh")
    )

    assert location.location_confidence == "uncertain"
    assert location.needs_user_confirmation is True
    assert location.display_name == "Vị trí hiện tại chưa xác định rõ"
    assert location.administrative_levels["province"] is None


def test_search_long_tien_candidate() -> None:
    # Mock OpenMeteo client to return Cai Lay/Long Tien
    mock_client = MagicMock()
    mock_client.search_city = AsyncMock(
        return_value={
            "results": [
                {
                    "name": "Long Tien",
                    "country": "Vietnam",
                    "country_code": "VN",
                    "latitude": 10.3502,
                    "longitude": 106.1406,
                    "timezone": "Asia/Ho_Chi_Minh",
                    "admin1": "Tien Giang",
                }
            ]
        }
    )

    service = GeocodingService(mock_client)
    # Mock providers to return empty list so it falls back to OpenMeteo client search
    service._openweather_provider.geocode = AsyncMock(return_value=[])
    service._nominatim_provider.geocode = AsyncMock(return_value=[])

    results = asyncio.run(service.search_locations("Long Tien"))
    assert len(results) > 0
    candidate = results[0]
    assert candidate.city == "Long Tien"
    assert candidate.location_confidence == "commune"
    assert candidate.display_name == "Long Tien, Tien Giang"
    assert candidate.short_display_name == "Long Tien, Tien Giang"
    assert candidate.administrative_levels["province"] == "Tien Giang"
