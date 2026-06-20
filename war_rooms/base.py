"""Base War Room — shared infrastructure for all command centers."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING, Any

from core.models import WarRoom

if TYPE_CHECKING:
    from core.event_bus import EventBus


class BaseWarRoom(ABC):
    """A War Room activates during a high-stakes event and coordinates all divisions."""

    war_room: WarRoom

    def __init__(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus
        self.activated_at: datetime | None = None
        self.deactivated_at: datetime | None = None
        self.is_active = False
        self.log: list[dict[str, Any]] = []
        self.logger = logging.getLogger(f"sfc.war_room.{self.war_room.value}")

    def activate(self, context: dict[str, Any] | None = None) -> None:
        self.is_active = True
        self.activated_at = datetime.utcnow()
        self.logger.info("[WarRoom:%s] ACTIVATED — %s", self.war_room.value, context)
        self._on_activate(context or {})

    def deactivate(self, summary: dict[str, Any] | None = None) -> None:
        self.is_active = False
        self.deactivated_at = datetime.utcnow()
        self.logger.info("[WarRoom:%s] DEACTIVATED", self.war_room.value)
        self._on_deactivate(summary or {})

    def record(self, event: str, payload: dict[str, Any] | None = None) -> None:
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": event,
            "payload": payload or {},
        }
        self.log.append(entry)

    @abstractmethod
    def _on_activate(self, context: dict[str, Any]) -> None: ...

    @abstractmethod
    def _on_deactivate(self, summary: dict[str, Any]) -> None: ...

    def get_log(self) -> list[dict[str, Any]]:
        return list(self.log)
