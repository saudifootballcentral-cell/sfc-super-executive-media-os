"""Event Bus — the central nervous system of SFC Super Executive Media OS."""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from datetime import datetime
from typing import Any, Awaitable, Callable
from uuid import uuid4

from core.models import Division, EventType, SFCEvent

logger = logging.getLogger("sfc.event_bus")

Handler = Callable[[SFCEvent], Awaitable[None] | None]


class EventBus:
    """Async publish/subscribe event bus.

    Standard flow enforced by subscription order:
    Event → Intelligence → Editorial → Creative → Governance → Publishing → Analytics → Learning
    """

    PIPELINE_ORDER: list[Division] = [
        Division.INTELLIGENCE,
        Division.EDITORIAL,
        Division.CREATIVE,
        Division.GOVERNANCE,
        Division.PUBLISHING,
        Division.ANALYTICS,
    ]

    def __init__(self) -> None:
        self._subscribers: dict[EventType, list[tuple[Division | None, Handler]]] = defaultdict(list)
        self._global_subscribers: list[tuple[Division | None, Handler]] = []
        self._event_log: list[SFCEvent] = []

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def subscribe(
        self,
        event_type: EventType,
        handler: Handler,
        division: Division | None = None,
    ) -> None:
        self._subscribers[event_type].append((division, handler))
        logger.debug("Subscribed %s to %s", division or "global", event_type)

    def subscribe_all(self, handler: Handler, division: Division | None = None) -> None:
        self._global_subscribers.append((division, handler))

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    async def publish(self, event: SFCEvent) -> None:
        event.status = "processing"
        self._event_log.append(event)
        logger.info("[EventBus] %s | %s | source=%s", event.event_id, event.event_type, event.source)

        handlers: list[tuple[Division | None, Handler]] = (
            self._global_subscribers + self._subscribers.get(EventType(event.event_type), [])
        )

        for division, handler in handlers:
            try:
                result = handler(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as exc:
                logger.error("[EventBus] Handler %s failed: %s", handler.__name__, exc, exc_info=True)

        event.status = "processed"

    def publish_sync(self, event: SFCEvent) -> None:
        asyncio.get_event_loop().run_until_complete(self.publish(event))

    # ------------------------------------------------------------------
    # Factory helpers
    # ------------------------------------------------------------------

    def create_event(
        self,
        event_type: EventType,
        source: str,
        payload: dict[str, Any] | None = None,
        owner: Division | None = None,
    ) -> SFCEvent:
        return SFCEvent(
            event_type=event_type,
            source=source,
            payload=payload or {},
            owner=owner,
        )

    # ------------------------------------------------------------------
    # Log access
    # ------------------------------------------------------------------

    @property
    def event_log(self) -> list[SFCEvent]:
        return list(self._event_log)

    def get_events_by_type(self, event_type: EventType) -> list[SFCEvent]:
        return [e for e in self._event_log if e.event_type == event_type]

    def get_events_by_status(self, status: str) -> list[SFCEvent]:
        return [e for e in self._event_log if e.status == status]
