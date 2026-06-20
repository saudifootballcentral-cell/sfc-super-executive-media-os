"""Global Memory — shared organization-wide knowledge store."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

logger = logging.getLogger("sfc.memory.global")


class GlobalMemory:
    """Shared organization memory accessible by all divisions.

    Contains: Players, Clubs, Competitions, Coaches, Sponsors,
    Journalists, Historical Content, Brand Rules, Analytics.
    """

    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {
            "players": {},
            "clubs": {},
            "competitions": {},
            "coaches": {},
            "sponsors": {},
            "journalists": {},
            "historical_content": {},
            "brand_rules": {},
            "analytics": {},
        }

    # ------------------------------------------------------------------
    # Generic CRUD
    # ------------------------------------------------------------------

    def set(self, namespace: str, key: str, value: Any) -> None:
        if namespace not in self._store:
            self._store[namespace] = {}
        self._store[namespace][key] = value
        logger.debug("[GlobalMemory] SET %s/%s", namespace, key)

    def get(self, namespace: str, key: str, default: Any = None) -> Any:
        return self._store.get(namespace, {}).get(key, default)

    def delete(self, namespace: str, key: str) -> bool:
        ns = self._store.get(namespace, {})
        if key in ns:
            del ns[key]
            logger.debug("[GlobalMemory] DEL %s/%s", namespace, key)
            return True
        return False

    def list_keys(self, namespace: str) -> list[str]:
        return list(self._store.get(namespace, {}).keys())

    def get_all(self, namespace: str) -> dict[str, Any]:
        return dict(self._store.get(namespace, {}))

    # ------------------------------------------------------------------
    # Typed helpers
    # ------------------------------------------------------------------

    def register_player(self, player_id: str, data: dict[str, Any]) -> None:
        self.set("players", player_id, data)

    def get_player(self, player_id: str) -> dict[str, Any] | None:
        return self.get("players", player_id)

    def register_club(self, club_id: str, data: dict[str, Any]) -> None:
        self.set("clubs", club_id, data)

    def get_club(self, club_id: str) -> dict[str, Any] | None:
        return self.get("clubs", club_id)

    def register_competition(self, competition_id: str, data: dict[str, Any]) -> None:
        self.set("competitions", competition_id, data)

    def set_brand_rule(self, rule_name: str, rule: Any) -> None:
        self.set("brand_rules", rule_name, rule)

    def get_brand_rule(self, rule_name: str) -> Any:
        return self.get("brand_rules", rule_name)

    def record_analytics(self, metric_key: str, value: Any) -> None:
        self.set("analytics", metric_key, value)

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> dict[str, dict[str, Any]]:
        return {ns: dict(data) for ns, data in self._store.items()}
