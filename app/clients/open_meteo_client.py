from typing import Any

import httpx

from app.core.config import Settings
from app.core.exceptions import InvalidWeatherDataError, WeatherProviderError
from app.services.weather_cache import AsyncTTLCache


class OpenMeteoClient:
    """Async client responsible only for Open-Meteo HTTP calls."""

    def __init__(self, settings: Settings, cache: AsyncTTLCache | None = None) -> None:
        self._forecast_url = settings.open_meteo_forecast_url
        self._geocoding_url = settings.open_meteo_geocoding_url
        self._timeout = settings.http_timeout_seconds
        self._cache = cache

    async def search_city(self, city: str, *, count: int = 10, language: str = "en") -> dict[str, Any]:
        return await self._get_json(
            self._geocoding_url,
            params={
                "name": city,
                "count": count,
                "language": language,
                "format": "json",
            },
            ttl_seconds=24 * 60 * 60,
        )

    async def get_forecast(
        self,
        *,
        latitude: float,
        longitude: float,
        timezone: str,
        forecast_days: int,
    ) -> dict[str, Any]:
        return await self._get_json(
            self._forecast_url,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": ",".join(
                    [
                        "temperature_2m",
                        "relative_humidity_2m",
                        "apparent_temperature",
                        "is_day",
                        "precipitation",
                        "rain",
                        "showers",
                        "weather_code",
                        "cloud_cover",
                        "surface_pressure",
                        "visibility",
                        "wind_speed_10m",
                        "wind_direction_10m",
                    ],
                ),
                "hourly": ",".join(
                    [
                        "temperature_2m",
                        "apparent_temperature",
                        "relative_humidity_2m",
                        "precipitation_probability",
                        "precipitation",
                        "rain",
                        "weather_code",
                        "wind_speed_10m",
                        "uv_index",
                        "is_day",
                        "visibility",
                    ],
                ),
                "daily": ",".join(
                    [
                        "weather_code",
                        "temperature_2m_max",
                        "temperature_2m_min",
                        "precipitation_probability_max",
                        "rain_sum",
                        "wind_speed_10m_max",
                        "uv_index_max",
                        "sunrise",
                        "sunset",
                    ],
                ),
                "forecast_days": forecast_days,
                "timezone": timezone or "auto",
            },
            ttl_seconds=5 * 60,
        )

    async def _get_json(self, url: str, *, params: dict[str, Any], ttl_seconds: int) -> dict[str, Any]:
        if self._cache is None:
            return await self._get_json_uncached(url, params=params)

        return await self._cache.get_or_create(
            _build_http_cache_key(url, params),
            ttl_seconds=ttl_seconds,
            factory=lambda: self._get_json_uncached(url, params=params),
        )

    async def _get_json_uncached(self, url: str, *, params: dict[str, Any]) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
        except httpx.TimeoutException as exc:
            raise WeatherProviderError("Open-Meteo timeout.") from exc
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                raise WeatherProviderError(
                    "Open-Meteo returned HTTP 429.",
                    public_message="Dịch vụ thời tiết đang bị giới hạn tạm thời. Vui lòng thử lại sau ít phút.",
                    status_code=503,
                ) from exc
            raise WeatherProviderError(f"Open-Meteo returned HTTP {exc.response.status_code}.") from exc
        except httpx.HTTPError as exc:
            raise WeatherProviderError("Cannot connect to Open-Meteo.") from exc
        except ValueError as exc:
            raise InvalidWeatherDataError("Open-Meteo returned invalid JSON.") from exc

        if not isinstance(data, dict):
            raise InvalidWeatherDataError("Open-Meteo returned unexpected data.")
        return data


def _build_http_cache_key(url: str, params: dict[str, Any]) -> tuple[object, ...]:
    normalized_params = tuple(sorted((key, _normalize_param_value(value)) for key, value in params.items()))
    return ("open-meteo-http", url, normalized_params)


def _normalize_param_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)
