from dataclasses import dataclass
from math import atan2, cos, radians, sin, sqrt

from app.core.config import get_settings
from app.models.domain import Location
from app.providers.location.bigdatacloud import BigDataCloudProvider
from app.providers.location.nominatim import NominatimProvider
from app.providers.location.openweather import OpenWeatherGeocodingProvider
from app.utils.location_normalizer import (
    VIETNAM_LOCATION_FALLBACKS,
    LocationFallback,
    normalize_location_key,
)

EARTH_RADIUS_KM = 6371.0
MAX_NEAREST_LOCATION_DISTANCE_KM = 90.0


@dataclass(frozen=True)
class ResolvedLocationDisplay:
    city: str
    country: str
    timezone: str
    location_name: str
    display_name: str
    short_display_name: str | None = None
    administrative_levels: dict[str, str | None] | None = None
    location_confidence: str = "exact"
    location_provider: str = "fallback"
    needs_user_confirmation: bool = False
    location_candidates: list[str] | None = None


class LocationDisplayService:
    """Builds user-facing location labels without blocking weather requests."""

    def __init__(self) -> None:
        self._coordinate_cache: dict[tuple[float, float], ResolvedLocationDisplay] = {}
        self._api_cache: dict[tuple[float, float], tuple[str | None, str | None, list[str], str]] = {}
        settings = get_settings()
        self._openweather_provider = OpenWeatherGeocodingProvider(settings)
        self._nominatim_provider = NominatimProvider()
        self._bigdatacloud_provider = BigDataCloudProvider()

    def enrich_city_location(self, location: Location) -> Location:
        display_name = location.display_name or location.location_name or location.city
        return Location(
            city=location.city,
            country=location.country,
            latitude=location.latitude,
            longitude=location.longitude,
            timezone=location.timezone,
            source="city",
            location_name=location.location_name or location.city,
            display_name=display_name,
            accuracy_meters=location.accuracy_meters,
            location_confidence="exact",
            location_provider=location.location_provider or "fallback",
        )

    async def resolve_coordinates(
        self,
        *,
        latitude: float,
        longitude: float,
        timezone: str,
        accuracy_meters: float | None = None,
    ) -> Location:
        cache_key = (round(latitude, 4), round(longitude, 4))
        display = self._coordinate_cache.get(cache_key)
        if display is None:
            display = await self._resolve_coordinates_uncached(
                latitude=latitude,
                longitude=longitude,
                timezone=timezone,
            )
            self._coordinate_cache[cache_key] = display

        needs_user_confirmation = display.needs_user_confirmation
        display_name = display.display_name
        short_display_name = display.short_display_name
        confidence = display.location_confidence
        admin_levels = display.administrative_levels

        if accuracy_meters is not None and accuracy_meters > 500.0:
            needs_user_confirmation = True
            display_name = "Vị trí hiện tại chưa xác định rõ"
            short_display_name = "Vị trí hiện tại chưa xác định rõ"
            confidence = "uncertain"
            admin_levels = {
                "hamlet": None,
                "ward_or_commune": None,
                "district": None,
                "province": None,
                "country": "Vietnam",
            }
        elif confidence in ("uncertain", "coordinates"):
            needs_user_confirmation = True
            display_name = "Vị trí hiện tại chưa xác định rõ"
            short_display_name = "Vị trí hiện tại chưa xác định rõ"
            admin_levels = {
                "hamlet": None,
                "ward_or_commune": None,
                "district": None,
                "province": None,
                "country": "Vietnam",
            }

        return Location(
            city=display.city,
            country=display.country,
            latitude=latitude,
            longitude=longitude,
            timezone=display.timezone,
            source="coordinates",
            location_name=display.location_name,
            display_name=display_name,
            short_display_name=short_display_name,
            administrative_levels=admin_levels,
            accuracy_meters=accuracy_meters,
            location_confidence=confidence,
            location_provider=display.location_provider,
            needs_user_confirmation=needs_user_confirmation,
            location_candidates=display.location_candidates or [],
        )

    async def _resolve_coordinates_uncached(
        self, *, latitude: float, longitude: float, timezone: str
    ) -> ResolvedLocationDisplay:
        nearest = self._find_nearest_fallback(latitude=latitude, longitude=longitude)

        fallback_province_name = "Unknown"
        fallback_country = "Vietnam"
        fallback_timezone = timezone

        if nearest is not None:
            fallback, distance_km = nearest
            if distance_km <= MAX_NEAREST_LOCATION_DISTANCE_KM:
                fallback_province_name = fallback["name"]
                fallback_country = fallback["country"]
                fallback_timezone = timezone if timezone != "auto" else fallback["timezone"]

        if fallback_province_name == "Unknown":
            return ResolvedLocationDisplay(
                city="Vị trí hiện tại",
                country="Unknown",
                timezone=timezone or "auto",
                location_name="Vị trí hiện tại",
                display_name="Vị trí hiện tại chưa xác định rõ",
                short_display_name="Vị trí hiện tại chưa xác định rõ",
                administrative_levels={
                    "hamlet": None,
                    "ward_or_commune": None,
                    "district": None,
                    "province": None,
                    "country": "Unknown",
                },
                location_confidence="coordinates",
                location_provider="fallback",
                needs_user_confirmation=True,
                location_candidates=[],
            )

        local_prov_key = normalize_location_key(fallback_province_name)

        # Query reverse geocoding API
        res = await self._query_reverse_geocoding(latitude, longitude)
        if len(res) == 3:
            locality, api_province, api_names = res
            admin_levels = None
            provider_name = "fallback"
        elif len(res) == 4:
            locality, api_province, api_names, admin_levels = res
            provider_name = "fallback"
        else:
            locality, api_province, api_names, admin_levels, provider_name = res

        # Check if the local fallback province name matches any name in the API responses
        is_valid_match = False
        for api_name in api_names:
            api_name_key = normalize_location_key(api_name)
            if api_name_key == local_prov_key or local_prov_key in api_name_key or api_name_key in local_prov_key:
                is_valid_match = True
                break

        if is_valid_match:
            if admin_levels is None:
                # Mock or provider fallback
                ward_or_commune = None
                district = locality if locality != fallback_province_name else None
                province = fallback_province_name
                country = fallback_country
                hamlet = None
                admin_levels = {
                    "hamlet": hamlet,
                    "ward_or_commune": ward_or_commune,
                    "district": district,
                    "province": province,
                    "country": country,
                }
            else:
                # Ensure province matches fallback province
                admin_levels = dict(admin_levels)
                if not admin_levels.get("province"):
                    admin_levels["province"] = fallback_province_name
                if not admin_levels.get("country"):
                    admin_levels["country"] = fallback_country

            ward = admin_levels.get("ward_or_commune")
            dist = admin_levels.get("district")
            prov = admin_levels.get("province")

            ward = ward.strip() if ward else None
            dist = dist.strip() if dist else None
            prov = prov.strip() if prov else None

            # Confidence rules
            if ward and dist and prov:
                confidence = "exact"
                needs_conf = False
                display_name = f"{ward}, {dist}, {prov}"
                short_display_name = f"{ward}, {prov}"
                location_name = ward
            elif ward and prov:
                confidence = "commune"
                needs_conf = False
                display_name = f"{ward}, {prov}"
                short_display_name = f"{ward}, {prov}"
                location_name = ward
            elif dist and prov:
                confidence = "district"
                needs_conf = False
                display_name = f"{dist}, {prov}"
                short_display_name = f"{dist}, {prov}"
                location_name = dist
            elif prov:
                confidence = "province"
                needs_conf = True
                display_name = prov
                short_display_name = prov
                location_name = prov
            else:
                confidence = "coordinates"
                needs_conf = True
                display_name = "Vị trí hiện tại chưa xác định rõ"
                short_display_name = "Vị trí hiện tại chưa xác định rõ"
                location_name = "Vị trí hiện tại"

            return ResolvedLocationDisplay(
                city=fallback_province_name,
                country=fallback_country,
                timezone=fallback_timezone,
                location_name=location_name,
                display_name=display_name,
                short_display_name=short_display_name,
                administrative_levels=admin_levels,
                location_confidence=confidence,
                location_provider=provider_name,
                needs_user_confirmation=needs_conf,
                location_candidates=[],
            )

        # Mismatch or API failure -> Uncertain fallback
        # Do not guess the province name.
        candidates_clean = list(set([c.strip() for c in api_names if c.strip()]))
        return ResolvedLocationDisplay(
            city="Vị trí hiện tại",
            country=fallback_country,
            timezone=fallback_timezone or "auto",
            location_name="Vị trí hiện tại",
            display_name="Vị trí hiện tại chưa xác định rõ",
            short_display_name="Vị trí hiện tại chưa xác định rõ",
            administrative_levels={
                "hamlet": None,
                "ward_or_commune": None,
                "district": None,
                "province": None,
                "country": fallback_country,
            },
            location_confidence="uncertain",
            location_provider="fallback",
            needs_user_confirmation=True,
            location_candidates=candidates_clean,
        )

    async def _query_reverse_geocoding(
        self, latitude: float, longitude: float
    ) -> tuple[str | None, str | None, list[str], dict[str, str | None] | None, str]:
        # Cache reverse geocoding at 3 decimal places (~110m precision)
        cache_key = (round(latitude, 3), round(longitude, 3))
        if cache_key in self._api_cache:
            return self._api_cache[cache_key]

        providers = [
            self._openweather_provider,
            self._nominatim_provider,
            self._bigdatacloud_provider,
        ]

        for provider in providers:
            try:
                res = await provider.reverse_geocode(latitude, longitude)
                if len(res) == 3:
                    locality, province, api_names = res
                    admin_levels = None
                else:
                    locality, province, api_names, admin_levels = res
                if api_names:
                    result = (locality, province, api_names, admin_levels, provider.name)
                    self._api_cache[cache_key] = result
                    return result
            except Exception:
                continue

        return None, None, [], None, "fallback"

    def _find_nearest_fallback(self, *, latitude: float, longitude: float) -> tuple[LocationFallback, float] | None:
        nearest: tuple[LocationFallback, float] | None = None
        seen: set[tuple[float, float]] = set()
        for fallback in VIETNAM_LOCATION_FALLBACKS.values():
            coordinates = (fallback["latitude"], fallback["longitude"])
            if coordinates in seen:
                continue
            seen.add(coordinates)
            distance_km = _distance_km(
                latitude,
                longitude,
                fallback["latitude"],
                fallback["longitude"],
            )
            if nearest is None or distance_km < nearest[1]:
                nearest = (fallback, distance_km)
        return nearest


def _distance_km(latitude_a: float, longitude_a: float, latitude_b: float, longitude_b: float) -> float:
    lat_a = radians(latitude_a)
    lat_b = radians(latitude_b)
    delta_lat = radians(latitude_b - latitude_a)
    delta_lon = radians(longitude_b - longitude_a)

    haversine = sin(delta_lat / 2) ** 2 + cos(lat_a) * cos(lat_b) * sin(delta_lon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * atan2(sqrt(haversine), sqrt(1 - haversine))
