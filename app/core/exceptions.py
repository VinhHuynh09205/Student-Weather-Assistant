class CityNotFoundError(Exception):
    """Raised when Open-Meteo geocoding cannot resolve the requested city."""


class WeatherProviderError(Exception):
    """Raised when Open-Meteo cannot provide a usable response."""

    def __init__(
        self,
        message: str,
        *,
        public_message: str | None = None,
        status_code: int = 502,
    ) -> None:
        super().__init__(message)
        self.public_message = public_message or message
        self.status_code = status_code


class InvalidWeatherDataError(Exception):
    """Raised when weather provider data is missing or malformed."""
