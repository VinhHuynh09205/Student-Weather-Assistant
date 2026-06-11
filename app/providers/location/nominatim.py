from typing import Any

import httpx

from app.providers.location.base import BaseLocationProvider


class NominatimProvider(BaseLocationProvider):
    def __init__(self) -> None:
        self._timeout = 1.0
        self._headers = {"User-Agent": "StudentWeatherAssistant/1.0"}

    @property
    def name(self) -> str:
        return "nominatim"

    async def reverse_geocode(
        self, latitude: float, longitude: float
    ) -> tuple[str | None, str | None, list[str], dict[str, str | None] | None]:
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {
            "lat": latitude,
            "lon": longitude,
            "format": "json",
            "accept-language": "vi",
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(url, params=params, headers=self._headers)
                if response.status_code == 200:
                    data = response.json()
                    address = data.get("address", {})

                    province = address.get("state") or address.get("province") or address.get("region")

                    # hamlet
                    hamlet = address.get("hamlet") or address.get("isolated_dwelling")

                    # ward_or_commune
                    ward_or_commune = (
                        address.get("village")
                        or address.get("commune")
                        or address.get("suburb")
                        or address.get("ward")
                        or address.get("town")
                        or address.get("neighbourhood")
                        or address.get("quarter")
                    )

                    # district
                    district = (
                        address.get("district")
                        or address.get("county")
                        or address.get("city_district")
                        or address.get("municipality")
                    )

                    city_val = address.get("city")
                    if not district and city_val and province and city_val != province:
                        district = city_val

                    country = address.get("country") or "Vietnam"

                    if ward_or_commune == district:
                        ward_or_commune = None
                    if ward_or_commune == province:
                        ward_or_commune = None
                    if district == province:
                        district = None

                    admin_levels = {
                        "hamlet": hamlet,
                        "ward_or_commune": ward_or_commune,
                        "district": district,
                        "province": province,
                        "country": country,
                    }

                    locality = ward_or_commune or district or province

                    api_names = []
                    for val in address.values():
                        if isinstance(val, str):
                            api_names.append(val)
                    if data.get("display_name"):
                        api_names.append(data.get("display_name"))

                    return locality, province, api_names, admin_levels
        except Exception:
            pass

        return None, None, [], None

    async def geocode(self, city: str) -> list[dict[str, Any]]:
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": city,
            "format": "json",
            "accept-language": "vi",
            "countrycodes": "vn",
            "limit": 5,
            "addressdetails": 1,
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(url, params=params, headers=self._headers)
                if response.status_code == 200:
                    data = response.json()
                    candidates = []
                    if isinstance(data, list):
                        for item in data:
                            address = item.get("address", {})

                            province = address.get("state") or address.get("province") or address.get("region")
                            hamlet = address.get("hamlet") or address.get("isolated_dwelling")
                            ward_or_commune = (
                                address.get("village")
                                or address.get("commune")
                                or address.get("suburb")
                                or address.get("ward")
                                or address.get("town")
                                or address.get("neighbourhood")
                                or address.get("quarter")
                            )
                            district = (
                                address.get("district")
                                or address.get("county")
                                or address.get("city_district")
                                or address.get("municipality")
                            )

                            city_val = address.get("city")
                            if not district and city_val and province and city_val != province:
                                district = city_val

                            country = address.get("country") or "Vietnam"

                            if ward_or_commune == district:
                                ward_or_commune = None
                            if ward_or_commune == province:
                                ward_or_commune = None
                            if district == province:
                                district = None

                            admin_levels = {
                                "hamlet": hamlet,
                                "ward_or_commune": ward_or_commune,
                                "district": district,
                                "province": province,
                                "country": country,
                            }

                            if ward_or_commune and district and province:
                                confidence = "exact"
                                display_name = f"{ward_or_commune}, {district}, {province}"
                                short_display_name = f"{ward_or_commune}, {province}"
                                name = ward_or_commune
                            elif ward_or_commune and province:
                                confidence = "commune"
                                display_name = f"{ward_or_commune}, {province}"
                                short_display_name = f"{ward_or_commune}, {province}"
                                name = ward_or_commune
                            elif district and province:
                                confidence = "district"
                                display_name = f"{district}, {province}"
                                short_display_name = f"{district}, {province}"
                                name = district
                            elif province:
                                confidence = "province"
                                display_name = province
                                short_display_name = province
                                name = province
                            else:
                                confidence = "coordinates"
                                display_name = item.get("display_name", city)
                                short_display_name = display_name
                                name = city

                            candidates.append(
                                {
                                    "name": name,
                                    "latitude": float(item["lat"]),
                                    "longitude": float(item["lon"]),
                                    "country": country,
                                    "country_code": "VN",
                                    "timezone": "auto",
                                    "state": province,
                                    "display_name": display_name,
                                    "short_display_name": short_display_name,
                                    "administrative_levels": admin_levels,
                                    "location_confidence": confidence,
                                }
                            )
                        return candidates
        except Exception:
            pass

        return []
