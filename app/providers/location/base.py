from abc import ABC, abstractmethod
from typing import Any


class BaseLocationProvider(ABC):
    """Abstract interface for direct and reverse geocoding providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the geocoding provider."""
        pass

    @abstractmethod
    async def reverse_geocode(
        self, latitude: float, longitude: float
    ) -> tuple[str | None, str | None, list[str], dict[str, str | None] | None]:
        """
        Resolve coordinates to names.
        Returns: (locality, province, all_api_names, administrative_levels)
        """
        pass

    @abstractmethod
    async def geocode(self, city: str) -> list[dict[str, Any]]:
        """
        Resolve city name to coordinate candidates.
        Each candidate should contain:
        {
            "name": str,
            "latitude": float,
            "longitude": float,
            "country": str,
            "country_code": str,
            "timezone": str,
            "state": str | None
        }
        """
        pass
