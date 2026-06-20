"""Event Bus Manager — extends EventBus with persistence, replay, DLQ, priority routing."""

from __future__ import annotations

import logging
import threading
from collections import deque, defaultdict
from collections.abc import Callable
from datetime import datetime
from typing import Any

from sfc.events.bus import EventBus, get_event_bus
from sfc.events.types import BaseEvent
from sfc.infrastructure.shared.types import ComponentHealth, HealthStatus

logger = logging.getLogger("sfc.infrastructure.event_bus_manager")

_MAX_LOG = 10_000


class EventBusManagerService:
    """Extends the existing EventBus with persistence, replay, DLQ, and priority routing.

    Event lifecycle: Published → Queued → Delivered → Processed → Archived

    Priority rules:
    - CRITICAL: crisis, governance escalation — processed first
    - HIGH: breaking news, urgent tasks
    - MEDIUM: standard content flow
    - LOW: analytics, learning
    """

    def __init__(self) -> None:
        self._bus: EventBus = get_event_bus()
        self._persistent_log: deque[BaseEvent] = deque(maxlen=_MAX_LOG)
        self._dlq: list[dict[str, Any]] = []
        self._workflow_tracker: dict[str, list[str]] = defaultdict(list)
        self._priority_queues: dict[str, deque[BaseEvent]] = {
            "critical": deque(),
            "high": deque(),
            "medium": deque(),
            "low": deque(),
        }
        self._handler_priorities: dict[str, str] = {}
        self._retry_counts: dict[str, int] = defaultdict(int)
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Subscription
    # ------------------------------------------------------------------

    def subscribe(
        self,
        event_type: str,
        handler: Callable[..., Any],
        priority: str = "medium",
    ) -> None:
        """Subscribe with priority routing."""
        self._bus.subscribe(event_type, handler)
        handler_key = f"{event_type}:{getattr(handler, '__name__', str(handler))}"
        with self._lock:
            self._handler_priorities[handler_key] = priority
        logger.debug("[EventBusManager] Subscribe: %s priority=%s", event_type, priority)

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    def publish(self, event: BaseEvent) -> None:
        """Publish with persistence + priority queuing."""
        with self._lock:
            self._persistent_log.append(event)
            priority = getattr(event, "priority", "medium")
            queue = self._priority_queues.get(priority, self._priority_queues["medium"])
            queue.append(event)
            self._workflow_tracker[event.run_id].append(event.event_type)

        self._bus.publish(event)
        logger.debug("[EventBusManager] Published: %s run=%s", event.event_type, event.run_id)

    def publish_many(self, events: list[BaseEvent]) -> None:
        """Publish a batch of events."""
        for event in events:
            self.publish(event)

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def get_event_log(
        self,
        event_type: str | None = None,
        run_id: str | None = None,
        limit: int = 100,
    ) -> list[BaseEvent]:
        """Query persistent log."""
        with self._lock:
            events = list(self._persistent_log)

        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if run_id:
            events = [e for e in events if e.run_id == run_id]

        return events[-limit:]

    def get_workflow_status(self, run_id: str) -> dict[str, Any]:
        """All events for a specific run."""
        with self._lock:
            event_types = list(self._workflow_tracker.get(run_id, []))
            events = [e for e in self._persistent_log if e.run_id == run_id]

        return {
            "run_id": run_id,
            "event_types": event_types,
            "event_count": len(events),
            "events": [
                {
                    "event_type": e.event_type,
                    "timestamp": e.timestamp.isoformat(),
                    "priority": e.priority,
                }
                for e in events
            ],
        }

    def get_dlq(self) -> list[dict[str, Any]]:
        """Inspect dead letter queue."""
        with self._lock:
            return list(self._dlq)

    def retry_dlq(self) -> int:
        """Retry all DLQ items. Returns count retried."""
        with self._lock:
            dlq_copy = list(self._dlq)
            self._dlq.clear()

        retried = 0
        for item in dlq_copy:
            event = item.get("event")
            if event and isinstance(event, BaseEvent):
                try:
                    self._bus.publish(event)
                    retried += 1
                    logger.info("[EventBusManager] DLQ retry success: %s", event.event_type)
                except Exception as exc:  # noqa: BLE001
                    logger.error("[EventBusManager] DLQ retry failed: %s", exc)
                    with self._lock:
                        self._dlq.append({**item, "last_retry_error": str(exc)})

        return retried

    def get_event_dashboard(self) -> dict[str, Any]:
        """Summary: total events, by type, recent activity, DLQ size."""
        with self._lock:
            events = list(self._persistent_log)
            dlq_size = len(self._dlq)
            active_workflows = len(self._workflow_tracker)

        by_type: dict[str, int] = defaultdict(int)
        by_priority: dict[str, int] = defaultdict(int)
        for event in events:
            by_type[event.event_type] += 1
            by_priority[getattr(event, "priority", "medium")] += 1

        recent = events[-10:]

        return {
            "total_events": len(events),
            "by_type": dict(by_type),
            "by_priority": dict(by_priority),
            "dlq_size": dlq_size,
            "active_workflows": active_workflows,
            "recent_events": [
                {
                    "event_type": e.event_type,
                    "run_id": e.run_id,
                    "timestamp": e.timestamp.isoformat(),
                    "priority": e.priority,
                }
                for e in recent
            ],
            "priority_queue_sizes": {
                name: len(q) for name, q in self._priority_queues.items()
            },
        }

    def health_check(self) -> ComponentHealth:
        """Return health status of the event bus manager."""
        try:
            with self._lock:
                total = len(self._persistent_log)
                dlq_size = len(self._dlq)

            errors: list[str] = []
            status = HealthStatus.HEALTHY

            if dlq_size > 100:
                errors.append(f"DLQ has {dlq_size} unprocessed events")
                status = HealthStatus.DEGRADED

            return ComponentHealth(
                component="event_bus_manager",
                status=status,
                last_check=datetime.utcnow(),
                metrics={
                    "total_events_logged": total,
                    "dlq_size": dlq_size,
                    "active_workflows": len(self._workflow_tracker),
                },
                errors=errors,
            )
        except Exception as exc:  # noqa: BLE001
            return ComponentHealth(
                component="event_bus_manager",
                status=HealthStatus.UNHEALTHY,
                last_check=datetime.utcnow(),
                metrics={},
                errors=[str(exc)],
            )
