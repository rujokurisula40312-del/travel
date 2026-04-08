"""Простой TTL-кеш для туров, PDF и конфига клиента.

Не использует Redis — только in-memory dict. Этого хватает для одного
инстанса бота. Если понадобится горизонтальное масштабирование — заменить
на aiocache + Redis.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any, Awaitable, Callable, Generic, TypeVar

T = TypeVar("T")


class TTLCache(Generic[T]):
    """Асинхронный кеш ключ → значение с временем жизни."""

    def __init__(self, ttl_seconds: float) -> None:
        self._ttl = ttl_seconds
        self._store: dict[str, tuple[float, T]] = {}
        self._lock = asyncio.Lock()

    async def get_or_load(
        self, key: str, loader: Callable[[], Awaitable[T]]
    ) -> T:
        now = time.monotonic()
        async with self._lock:
            cached = self._store.get(key)
            if cached and cached[0] > now:
                return cached[1]
        value = await loader()
        async with self._lock:
            self._store[key] = (now + self._ttl, value)
        return value

    async def invalidate(self, key: str | None = None) -> None:
        async with self._lock:
            if key is None:
                self._store.clear()
            else:
                self._store.pop(key, None)


# Глобальные кеши на разные сущности
client_config_cache: TTLCache[Any] = TTLCache(ttl_seconds=600)  # 10 мин
tours_cache: TTLCache[Any] = TTLCache(ttl_seconds=300)  # 5 мин
pdf_cache: TTLCache[bytes] = TTLCache(ttl_seconds=3600)  # 1 час


async def reset_all() -> None:
    """Сбрасывает все кеши (вызывается командой /reload)."""
    await client_config_cache.invalidate()
    await tours_cache.invalidate()
    await pdf_cache.invalidate()
