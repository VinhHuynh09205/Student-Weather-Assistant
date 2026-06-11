import asyncio

import httpx
import pytest

from app.clients.open_meteo_client import OpenMeteoClient
from app.core.config import Settings
from app.core.exceptions import WeatherProviderError


class TimeoutAsyncClient:
    def __init__(self, *, timeout: float) -> None:
        self.timeout = timeout

    async def __aenter__(self) -> "TimeoutAsyncClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def get(self, url: str, *, params: dict[str, object]) -> httpx.Response:
        raise httpx.TimeoutException("request timed out")


class RateLimitedAsyncClient:
    def __init__(self, *, timeout: float) -> None:
        self.timeout = timeout

    async def __aenter__(self) -> "RateLimitedAsyncClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def get(self, url: str, *, params: dict[str, object]) -> httpx.Response:
        return httpx.Response(
            status_code=429,
            request=httpx.Request("GET", url, params=params),
        )


def test_open_meteo_timeout_maps_to_provider_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(httpx, "AsyncClient", TimeoutAsyncClient)
    client = OpenMeteoClient(Settings())

    with pytest.raises(WeatherProviderError, match="timeout"):
        asyncio.run(client.search_city("Can Tho"))


def test_open_meteo_429_maps_to_friendly_provider_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(httpx, "AsyncClient", RateLimitedAsyncClient)
    client = OpenMeteoClient(Settings())

    with pytest.raises(WeatherProviderError) as exc_info:
        asyncio.run(client.search_city("Can Tho"))

    assert str(exc_info.value) == "Open-Meteo returned HTTP 429."
    assert exc_info.value.status_code == 503
    assert exc_info.value.public_message == (
        "Dịch vụ thời tiết đang bị giới hạn tạm thời. Vui lòng thử lại sau ít phút."
    )
