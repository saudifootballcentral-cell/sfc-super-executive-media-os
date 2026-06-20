"""Global Memory — shared organization-wide knowledge store.

Namespaces: players, clubs, competitions, coaches, sponsors,
journalists, historical_content, brand_rules, analytics.

Package 2+: Backed by Redis or PostgreSQL for persistence and
distributed access across concurrent pipeline runs.
"""

from __future__ import annotations

import logging
import threading
from typing import Any

logger = logging.getLogger("sfc.memory.global")

_NAMESPACES = [
    "players", "clubs", "competitions", "coaches", "sponsors",
    "journalists", "historical_content", "brand_rules", "analytics",
]


class GlobalMemory:
    """Thread-safe shared organization memory accessible by all divisions and nodes."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {ns: {} for ns in _NAMESPACES}
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Generic CRUD
    # ------------------------------------------------------------------

    def set(self, namespace: str, key: str, value: Any) -> None:
        with self._lock:
            if namespace not in self._store:
                self._store[namespace] = {}
            self._store[namespace][key] = value
        logger.debug("[GlobalMemory] SET %s/%s", namespace, key)

    def get(self, namespace: str, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._store.get(namespace, {}).get(key, default)

    def delete(self, namespace: str, key: str) -> bool:
        with self._lock:
            ns = self._store.get(namespace, {})
            if key in ns:
                del ns[key]
                return True
        return False

    def list_keys(self, namespace: str) -> list[str]:
        with self._lock:
            return list(self._store.get(namespace, {}).keys())

    def get_all(self, namespace: str) -> dict[str, Any]:
        with self._lock:
            return dict(self._store.get(namespace, {}))

    # ------------------------------------------------------------------
    # Typed convenience methods
    # ------------------------------------------------------------------

    def register_player(self, player_id: str, data: dict[str, Any]) -> None:
        self.set("players", player_id, data)

    def get_player(self, player_id: str) -> dict[str, Any] | None:
        return self.get("players", player_id)

    def register_club(self, club_id: str, data: dict[str, Any]) -> None:
        self.set("clubs", club_id, data)

    def get_club(self, club_id: str) -> dict[str, Any] | None:
        return self.get("clubs", club_id)

    def set_brand_rule(self, rule_name: str, rule: Any) -> None:
        self.set("brand_rules", rule_name, rule)

    def get_brand_rule(self, rule_name: str) -> Any:
        return self.get("brand_rules", rule_name)

    def record_analytics(self, key: str, value: Any) -> None:
        self.set("analytics", key, value)

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            return {ns: dict(data) for ns, data in self._store.items()}

    def total_entries(self) -> int:
        with self._lock:
            return sum(len(v) for v in self._store.values())
