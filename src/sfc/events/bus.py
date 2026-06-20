"""Event bus for cross-division communication.

Events are fire-and-forget: publish() schedules handlers but never blocks.
Use asyncio.create_task() internally so callers are not held up.
"""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from collections.abc import Callable
from typing import Any

from sfc.events.types import BaseEvent

logger = logging.getLogger("sfc.events.bus")

_MAX_HISTORY = 100


class EventBus:
    """Thread-safe async event bus with subscription and history.

    Singleton — use get_event_bus() rather than instantiating directly.
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[Callable[..., Any]]] = {}
        self._history: deque[BaseEvent] = deque(maxlen=_MAX_HISTORY)
        self._lock = asyncio.Lock()

    def subscribe(self, event_type: str, handler: Callable[..., Any]) -> None:
        """Register handler for event_type. Thread-safe via dict operations."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.debug("[EventBus] %s subscribed to %s", handler.__name__, event_type)

    def publish(self, event: BaseEvent) -> None:
        """Deliver event to all matching handlers. Fire-and-forget."""
        self._history.append(event)
        handlers = self._handlers.get(event.event_type, [])
        if not handlers:
            return

        for handler in handlers:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._safe_call(handler, event))
            except RuntimeError:
                # No running event loop — call synchronously (test context)
                result = handler(event)
                if asyncio.iscoroutine(result):
                    asyncio.run(result)

    def publish_many(self, events: list[BaseEvent]) -> None:
        """Publish a batch of events."""
        for event in events:
            self.publish(event)

    def get_history(self, event_type: str | None = None) -> list[BaseEvent]:
        """Return up to last 100 events, optionally filtered by type."""
        if event_type is None:
            return list(self._history)
        return [e for e in self._history if e.event_type == event_type]

    async def _safe_call(self, handler: Callable[..., Any], event: BaseEvent) -> None:
        try:
            result = handler(event)
            if asyncio.iscoroutine(result):
                await result
        except Exception as exc:
            logger.error("[EventBus] Handler %s raised: %s", handler.__name__, exc)

    def reset(self) -> None:
        """Clear all subscriptions and history. For testing only."""
        self._handlers.clear()
        self._history.clear()


_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """Return the process-wide singleton EventBus."""
    global _bus
    if _bus is None:
        _bus = EventBus()
    return _bus
