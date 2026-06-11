from typing import Any

import httpx

from app.providers.location.base import BaseLocationProvider


class BigDataCloudProvider(BaseLocationProvider):
    def __init__(self) -> None:
        self._timeout = 1.0

    @property
    def name(self) -> str:
        return "bigdatacloud"

    async def reverse_geocode(
        self, latitude: float, longitude: float
    ) -> tuple[str | None, str | None, list[str], dict[str, str | None] | None]:
        url = "https://api.bigdatacloud.net/data/reverse-geocode-client"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "localityLanguage": "vi",
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=True) as client:
                response = await client.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    province = data.get("principalSubdivision")
                    district = data.get("city") or data.get("locality")
                    ward_or_commune = None
                    country = "Vietnam"

                    api_names = []
                    if province:
                        api_names.append(province)
                    if district:
                        api_names.append(district)

                    admin_items = data.get("localityInfo", {}).get("administrative", [])
                    for item in admin_items:
                        level = item.get("adminLevel")
                        name = item.get("name")
                        if level == 2:
                            country = name
                        elif level == 4:
                            province = name
                        elif level == 6:
                            district = name
                        elif level == 8:
                            ward_or_commune = name
                        if name:
                            api_names.append(name)

                    info_items = data.get("localityInfo", {}).get("informative", [])
                    hamlet = None
                    for item in info_items:
                        name = item.get("name")
                        desc = item.get("description", "").lower()
                        if name:
                            api_names.append(name)
                        if "hamlet" in desc or "village" in desc:
                            hamlet = name

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
                    return locality, province, api_names, admin_levels
        except Exception:
            pass

        return None, None, [], None

    async def geocode(self, city: str) -> list[dict[str, Any]]:
        # BigDataCloud does not offer a direct geocoding client in its free tier easily.
        return []
