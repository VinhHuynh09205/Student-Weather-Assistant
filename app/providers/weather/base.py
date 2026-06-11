from abc import ABC, abstractmethod

from app.models.domain import (
    CurrentWeatherReport,
    DailyForecastReport,
    HourlyForecastReport,
    Location,
)


class BaseWeatherProvider(ABC):
    """Abstract interface for weather data providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the weather provider."""
        pass

    @abstractmethod
    async def get_current_weather(self, location: Location) -> CurrentWeatherReport:
        """Fetch and normalize current weather for a location."""
        pass

    @abstractmethod
    async def get_hourly_forecast(self, location: Location, hours: int) -> HourlyForecastReport:
        """Fetch and normalize hourly forecast for a location."""
        pass

    @abstractmethod
    async def get_daily_forecast(self, location: Location, days: int) -> DailyForecastReport:
        """Fetch and normalize daily forecast for a location."""
        pass
