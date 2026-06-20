"""Division Memory — isolated memory namespace per division."""

from __future__ import annotations

import logging
import threading
from typing import Any

from sfc.core.models import Division

logger = logging.getLogger("sfc.memory.division")


class DivisionMemory:
    """Thread-safe isolated memory store for a single division."""

    def __init__(self, division: Division) -> None:
        self.division = division
        self._store: dict[str, Any] = {}
        self._lock = threading.RLock()

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._store[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._store.get(key, default)

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._store:
                del self._store[key]
                return True
        return False

    def keys(self) -> list[str]:
        with self._lock:
            return list(self._store.keys())

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._store)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()


class DivisionMemoryStore:
    """Registry of DivisionMemory instances, one per division."""

    def __init__(self) -> None:
        self._memories: dict[Division, DivisionMemory] = {
            div: DivisionMemory(div) for div in Division
        }

    def for_division(self, division: Division) -> DivisionMemory:
        return self._memories[division]

    def snapshot_all(self) -> dict[str, dict[str, Any]]:
        return {div.value: mem.snapshot() for div, mem in self._memories.items()}
