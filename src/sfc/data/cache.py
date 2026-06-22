"""TTL cache for provider responses — Package 10A."""

from __future__ import annotations

import time
from typing import Any


class DataCache:
    """Simple in-memory TTL cache keyed by (provider, query)."""

    def __init__(self, default_ttl_seconds: float = 900.0) -> None:
        self._default_ttl = default_ttl_seconds
        self._store: dict[str, tuple[Any, float]] = {}

    def get(self, provider: str, query: str) -> Any | None:
        key = f"{provider}:{query}"
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.monotonic() > expires_at:
            del self._store[key]
            return None
        return value

    def set(
        self, provider: str, query: str, value: Any, ttl: float | None = None
    ) -> None:
        key = f"{provider}:{query}"
        ttl = ttl if ttl is not None else self._default_ttl
        self._store[key] = (value, time.monotonic() + ttl)

    def invalidate(self, provider: str, query: str) -> None:
        self._store.pop(f"{provider}:{query}", None)

    def clear(self) -> None:
        self._store.clear()

    def __len__(self) -> int:
        return len(self._store)
