"""Base Division class — all divisions inherit from this."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from core.models import Division, SFCEvent

if TYPE_CHECKING:
    from core.event_bus import EventBus
    from core.memory.division_memory import DivisionMemory
    from core.memory.episodic_memory import EpisodicMemory


class BaseDivision(ABC):
    """Abstract base for all SFC divisions."""

    division: Division

    def __init__(
        self,
        event_bus: EventBus,
        memory: DivisionMemory,
        episodic: EpisodicMemory,
    ) -> None:
        self.event_bus = event_bus
        self.memory = memory
        self.episodic = episodic
        self.logger = logging.getLogger(f"sfc.division.{self.division.value}")

    @abstractmethod
    async def handle_event(self, event: SFCEvent) -> dict[str, Any] | None:
        """Process an incoming event. Return result payload or None."""
        ...

    def record_lesson(self, event: str, decision: str, result: str, lesson: str) -> None:
        self.episodic.record(
            event=event,
            decision=decision,
            result=result,
            lesson=lesson,
            division=self.division,
        )

    async def initialize(self) -> None:
        """Optional async initialization hook."""

    def status(self) -> dict[str, Any]:
        return {
            "division": self.division.value,
            "memory_keys": self.memory.keys(),
        }
