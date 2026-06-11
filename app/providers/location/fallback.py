from typing import Any

from app.providers.location.base import BaseLocationProvider


class SafeCoordinateFallbackProvider(BaseLocationProvider):
    @property
    def name(self) -> str:
        return "fallback"

    async def reverse_geocode(
        self, latitude: float, longitude: float
    ) -> tuple[str | None, str | None, list[str], dict[str, str | None] | None]:
        return None, None, [], None

    async def geocode(self, city: str) -> list[dict[str, Any]]:
        return []
