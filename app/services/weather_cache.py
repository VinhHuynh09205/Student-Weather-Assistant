import asyncio
from collections.abc import Awaitable, Callable, Hashable
from dataclasses import dataclass
from time import monotonic
from typing import Any, Generic, TypeVar, cast

T = TypeVar("T")


@dataclass(frozen=True)
class _CacheEntry(Generic[T]):
    value: T
    expires_at: float


class AsyncTTLCache:
    """Small in-memory async TTL cache with in-flight request deduplication."""

    def __init__(self, clock: Callable[[], float] = monotonic) -> None:
        self._clock = clock
        self._entries: dict[Hashable, _CacheEntry[Any]] = {}
        self._in_flight: dict[Hashable, asyncio.Task[Any]] = {}
        self._lock = asyncio.Lock()

    async def get_or_create(
        self,
        key: Hashable,
        *,
        ttl_seconds: int,
        factory: Callable[[], Awaitable[T]],
    ) -> T:
        now = self._clock()
        async with self._lock:
            entry = self._entries.get(key)
            if entry and entry.expires_at > now:
                return cast(T, entry.value)

            task = self._in_flight.get(key)
            created_task = task is None
            if task is None:
                task = asyncio.create_task(factory())
                self._in_flight[key] = task

        try:
            value = cast(T, await task)
        except Exception:
            if created_task:
                async with self._lock:
                    if self._in_flight.get(key) is task:
                        self._in_flight.pop(key, None)
            raise

        if created_task:
            async with self._lock:
                self._entries[key] = _CacheEntry(
                    value=value,
                    expires_at=self._clock() + ttl_seconds,
                )
                if self._in_flight.get(key) is task:
                    self._in_flight.pop(key, None)

        return value

    async def clear(self) -> None:
        async with self._lock:
            self._entries.clear()
            self._in_flight.clear()


def normalize_city_for_cache(city: str) -> str:
    return " ".join(city.strip().casefold().split())


def round_coordinate_for_cache(value: float, digits: int = 4) -> float:
    return round(value, digits)
