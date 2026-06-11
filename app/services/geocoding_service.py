from typing import Any

from app.clients.open_meteo_client import OpenMeteoClient
from app.core.config import get_settings
from app.core.exceptions import CityNotFoundError, InvalidWeatherDataError
from app.models.domain import Location
from app.providers.location.nominatim import NominatimProvider
from app.providers.location.openweather import OpenWeatherGeocodingProvider
from app.utils.location_normalizer import (
    VIETNAM_LOCATION_FALLBACKS,
    LocationFallback,
    build_location_candidates,
    get_location_fallback,
    normalize_location_key,
)

_GEOCODING_RESULT_COUNT = 10


class GeocodingService:
    """Resolves a city name to the location data needed by weather services."""

    def __init__(self, client: OpenMeteoClient) -> None:
        self._client = client
        settings = get_settings()
        self._openweather_provider = OpenWeatherGeocodingProvider(settings)
        self._nominatim_provider = NominatimProvider()

    async def search_locations(self, query: str) -> list[Location]:
        requested_city = query.strip()
        if not requested_city:
            return []

        results: list[Location] = []
        seen_coords: set[tuple[float, float]] = set()

        # 1. Check local fallbacks for partial/exact key or alias matches
        query_key = normalize_location_key(requested_city)
        if len(query_key) >= 2:
            for key, fallback in VIETNAM_LOCATION_FALLBACKS.items():
                if query_key == key or query_key in key or key in query_key:
                    coord = (round(fallback["latitude"], 4), round(fallback["longitude"], 4))
                    if coord not in seen_coords:
                        seen_coords.add(coord)
                        results.append(
                            Location(
                                city=fallback["name"],
                                country=fallback["country"],
                                latitude=fallback["latitude"],
                                longitude=fallback["longitude"],
                                timezone=fallback["timezone"],
                                location_provider="fallback",
                                display_name=f"{fallback['name']}, Vietnam",
                                short_display_name=fallback["name"],
                                administrative_levels={
                                    "hamlet": None,
                                    "ward_or_commune": None,
                                    "district": None,
                                    "province": fallback["name"],
                                    "country": fallback["country"],
                                },
                                location_confidence="province",
                            )
                        )

        # 2. Try OpenWeather Geocoding Direct
        try:
            candidates = await self._openweather_provider.geocode(requested_city)
            for c in candidates:
                if c["country_code"] == "VN" or normalize_location_key(c["country"]) in {"vietnam", "viet nam"}:
                    coord = (round(c["latitude"], 4), round(c["longitude"], 4))
                    if coord not in seen_coords:
                        seen_coords.add(coord)

                        name = c["name"]
                        province = c.get("state")
                        country = "Vietnam"

                        name_lower = name.lower() if name else ""
                        district_terms = ["huyện", "quan", "quận", "thị xã", "thi xa", "thành phố", "thanh pho"]
                        is_district = any(k in name_lower for k in district_terms)
                        if is_district:
                            district = name
                            ward_or_commune = None
                        else:
                            district = None
                            ward_or_commune = name
                        if ward_or_commune == province:
                            ward_or_commune = None
                        if district == province:
                            district = None

                        admin_levels = {
                            "hamlet": None,
                            "ward_or_commune": ward_or_commune,
                            "district": district,
                            "province": province,
                            "country": country,
                        }

                        if ward_or_commune and district and province:
                            confidence = "exact"
                            display_name = f"{ward_or_commune}, {district}, {province}"
                            short_display_name = f"{ward_or_commune}, {province}"
                        elif ward_or_commune and province:
                            confidence = "commune"
                            display_name = f"{ward_or_commune}, {province}"
                            short_display_name = f"{ward_or_commune}, {province}"
                        elif district and province:
                            confidence = "district"
                            display_name = f"{district}, {province}"
                            short_display_name = f"{district}, {province}"
                        elif province:
                            confidence = "province"
                            display_name = province
                            short_display_name = province
                        else:
                            confidence = "coordinates"
                            display_name = name or "Vietnam"
                            short_display_name = display_name

                        results.append(
                            Location(
                                city=c["name"],
                                country="Vietnam",
                                latitude=c["latitude"],
                                longitude=c["longitude"],
                                timezone=c["timezone"],
                                location_provider="openweather",
                                display_name=display_name,
                                short_display_name=short_display_name,
                                administrative_levels=admin_levels,
                                location_confidence=confidence,
                            )
                        )
        except Exception:
            pass

        # 3. Try Nominatim Geocoding
        try:
            candidates = await self._nominatim_provider.geocode(requested_city)
            for c in candidates:
                if c["country_code"] == "VN" or normalize_location_key(c["country"]) in {"vietnam", "viet nam"}:
                    coord = (round(c["latitude"], 4), round(c["longitude"], 4))
                    if coord not in seen_coords:
                        seen_coords.add(coord)
                        results.append(
                            Location(
                                city=c["name"],
                                country="Vietnam",
                                latitude=c["latitude"],
                                longitude=c["longitude"],
                                timezone=c["timezone"],
                                location_provider="nominatim",
                                display_name=c["display_name"],
                                short_display_name=c["short_display_name"],
                                administrative_levels=c["administrative_levels"],
                                location_confidence=c["location_confidence"],
                            )
                        )
        except Exception:
            pass

        # 4. Fallback search via OpenMeteo Client search
        for candidate in build_location_candidates(requested_city):
            try:
                data = await self._client.search_city(
                    candidate,
                    count=_GEOCODING_RESULT_COUNT,
                    language="en",
                )
                raw_results = data.get("results")
                if isinstance(raw_results, list):
                    for r in raw_results:
                        if isinstance(r, dict) and self._is_vietnam_result(r):
                            coord = (round(r["latitude"], 4), round(r["longitude"], 4))
                            if coord not in seen_coords:
                                seen_coords.add(coord)

                                name = r.get("name") or requested_city
                                province = r.get("admin1")

                                name_lower = name.lower() if name else ""
                                district_terms = ["huyện", "quan", "quận", "thị xã", "thi xa", "thành phố", "thanh pho"]
                                is_district = any(k in name_lower for k in district_terms)
                                if is_district:
                                    district = name
                                    ward_or_commune = None
                                else:
                                    district = None
                                    ward_or_commune = name
                                if ward_or_commune == province:
                                    ward_or_commune = None
                                if district == province:
                                    district = None

                                admin_levels = {
                                    "hamlet": None,
                                    "ward_or_commune": ward_or_commune,
                                    "district": district,
                                    "province": province,
                                    "country": "Vietnam",
                                }

                                if ward_or_commune and district and province:
                                    confidence = "exact"
                                    display_name = f"{ward_or_commune}, {district}, {province}"
                                    short_display_name = f"{ward_or_commune}, {province}"
                                elif ward_or_commune and province:
                                    confidence = "commune"
                                    display_name = f"{ward_or_commune}, {province}"
                                    short_display_name = f"{ward_or_commune}, {province}"
                                elif district and province:
                                    confidence = "district"
                                    display_name = f"{district}, {province}"
                                    short_display_name = f"{district}, {province}"
                                elif province:
                                    confidence = "province"
                                    display_name = province
                                    short_display_name = province
                                else:
                                    confidence = "coordinates"
                                    display_name = name
                                    short_display_name = display_name

                                results.append(
                                    Location(
                                        city=name,
                                        country="Vietnam",
                                        latitude=r["latitude"],
                                        longitude=r["longitude"],
                                        timezone=r.get("timezone") or "auto",
                                        location_provider="open_meteo",
                                        display_name=display_name,
                                        short_display_name=short_display_name,
                                        administrative_levels=admin_levels,
                                        location_confidence=confidence,
                                    )
                                )
            except Exception:
                pass

        return results

    async def find_city(self, city: str) -> Location:
        requested_city = city.strip()
        if not requested_city:
            raise CityNotFoundError("Tên địa điểm không được để trống.")

        # 1. Try OpenWeather Geocoding
        try:
            candidates = await self._openweather_provider.geocode(requested_city)
            vietnam_candidates = [
                c
                for c in candidates
                if c["country_code"] == "VN" or normalize_location_key(c["country"]) in {"vietnam", "viet nam"}
            ]
            if vietnam_candidates:
                first = vietnam_candidates[0]
                return Location(
                    city=first["name"],
                    country="Vietnam",
                    latitude=first["latitude"],
                    longitude=first["longitude"],
                    timezone=first["timezone"],
                    location_provider="openweather",
                )
        except Exception:
            pass

        # 2. Try OpenMeteo fallback
        fallback = get_location_fallback(requested_city)
        preferred_city_name = fallback["name"] if fallback is not None else None
        for candidate in build_location_candidates(requested_city):
            try:
                data = await self._client.search_city(
                    candidate,
                    count=_GEOCODING_RESULT_COUNT,
                    language="en",
                )
                vietnam_result = self._pick_vietnam_result(data.get("results"))
                if vietnam_result is not None:
                    loc = self._parse_location(
                        vietnam_result,
                        fallback_city=requested_city,
                        preferred_city_name=preferred_city_name,
                    )
                    return Location(
                        city=loc.city,
                        country=loc.country,
                        latitude=loc.latitude,
                        longitude=loc.longitude,
                        timezone=loc.timezone,
                        location_provider="open_meteo",
                    )
            except Exception:
                pass

        if fallback is not None:
            loc = self._location_from_fallback(fallback)
            return Location(
                city=loc.city,
                country=loc.country,
                latitude=loc.latitude,
                longitude=loc.longitude,
                timezone=loc.timezone,
                location_provider="fallback",
            )

        raise CityNotFoundError(f"Không tìm thấy địa điểm tại Việt Nam: {requested_city}")

    def _pick_vietnam_result(self, results: Any) -> dict[str, Any] | None:
        if not isinstance(results, list):
            return None

        for result in results:
            if isinstance(result, dict) and self._is_vietnam_result(result):
                return result
        return None

    def _is_vietnam_result(self, result: dict[str, Any]) -> bool:
        country_code = str(result.get("country_code") or "").strip().upper()
        country = normalize_location_key(str(result.get("country") or ""))
        return country_code == "VN" or country in {"vietnam", "viet nam"}

    def _parse_location(
        self,
        result: Any,
        *,
        fallback_city: str,
        preferred_city_name: str | None,
    ) -> Location:
        if not isinstance(result, dict):
            raise InvalidWeatherDataError("Geocoding response is invalid.")

        try:
            latitude = float(result["latitude"])
            longitude = float(result["longitude"])
        except (KeyError, TypeError, ValueError) as exc:
            raise InvalidWeatherDataError("Geocoding response misses coordinates.") from exc

        city = str(preferred_city_name or result.get("name") or fallback_city)
        country = str(result.get("country") or "")
        timezone = str(result.get("timezone") or "auto")

        return Location(
            city=city,
            country=country,
            latitude=latitude,
            longitude=longitude,
            timezone=timezone,
        )

    def _location_from_fallback(self, fallback: LocationFallback) -> Location:
        return Location(
            city=fallback["name"],
            country=fallback["country"],
            latitude=fallback["latitude"],
            longitude=fallback["longitude"],
            timezone=fallback["timezone"],
        )
