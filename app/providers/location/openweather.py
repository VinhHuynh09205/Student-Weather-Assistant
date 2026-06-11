from typing import Any

import httpx

from app.core.config import Settings
from app.providers.location.base import BaseLocationProvider


class OpenWeatherGeocodingProvider(BaseLocationProvider):
    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.openweather_api_key
        self._base_url = settings.openweather_base_url
        self._timeout = 1.0

    @property
    def name(self) -> str:
        return "openweather"

    async def reverse_geocode(
        self, latitude: float, longitude: float
    ) -> tuple[str | None, str | None, list[str], dict[str, str | None] | None]:
        if not self._api_key or self._api_key == "your_key_here":
            return None, None, [], None

        url = f"{self._base_url}/geo/1.0/reverse"
        params = {
            "lat": latitude,
            "lon": longitude,
            "limit": 5,
            "appid": self._api_key,
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list) and len(data) > 0:
                        first = data[0]
                        name = first.get("name")
                        local_names = first.get("local_names", {})
                        if local_names.get("vi"):
                            name = local_names["vi"]

                        province = first.get("state")
                        country = first.get("country", "Vietnam")
                        if country == "VN":
                            country = "Vietnam"

                        # Use is_district heuristic
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

                        locality = name

                        api_names = []
                        for item in data:
                            nm = item.get("name")
                            if nm:
                                api_names.append(nm)
                            st = item.get("state")
                            if st:
                                api_names.append(st)
                            l_names = item.get("local_names", {})
                            for val in l_names.values():
                                if isinstance(val, str):
                                    api_names.append(val)

                        return locality, province, api_names, admin_levels
        except Exception:
            pass

        return None, None, [], None

    async def geocode(self, city: str) -> list[dict[str, Any]]:
        if not self._api_key or self._api_key == "your_key_here":
            return []

        url = f"{self._base_url}/geo/1.0/direct"
        params = {
            "q": city,
            "limit": 5,
            "appid": self._api_key,
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    candidates = []
                    if isinstance(data, list):
                        for item in data:
                            name = item.get("name")
                            local_names = item.get("local_names", {})
                            if local_names.get("vi"):
                                name = local_names["vi"]

                            candidates.append(
                                {
                                    "name": name,
                                    "latitude": float(item["lat"]),
                                    "longitude": float(item["lon"]),
                                    "country": item.get("country", ""),
                                    "country_code": item.get("country", ""),
                                    "timezone": "auto",
                                    "state": item.get("state"),
                                }
                            )
                        return candidates
        except Exception:
            pass

        return []
