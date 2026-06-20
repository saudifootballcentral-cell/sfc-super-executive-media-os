"""Division Memory — isolated memory namespace per division."""

from __future__ import annotations

import logging
from typing import Any

from core.models import Division

logger = logging.getLogger("sfc.memory.division")


class DivisionMemory:
    """Dedicated memory store for a single division."""

    def __init__(self, division: Division) -> None:
        self.division = division
        self._store: dict[str, Any] = {}

    def set(self, key: str, value: Any) -> None:
        self._store[key] = value
        logger.debug("[DivisionMemory:%s] SET %s", self.division, key)

    def get(self, key: str, default: Any = None) -> Any:
        return self._store.get(key, default)

    def delete(self, key: str) -> bool:
        if key in self._store:
            del self._store[key]
            return True
        return False

    def keys(self) -> list[str]:
        return list(self._store.keys())

    def snapshot(self) -> dict[str, Any]:
        return dict(self._store)

    def clear(self) -> None:
        self._store.clear()
        logger.debug("[DivisionMemory:%s] CLEARED", self.division)


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
