"""Analytics Division — event definitions."""

from __future__ import annotations

from sfc.events.types import PerformanceUpdated

SUBSCRIBED_EVENTS: list[str] = ["publishing_completed"]
PUBLISHED_EVENTS: list[str] = ["performance_updated"]

__all__ = ["SUBSCRIBED_EVENTS", "PUBLISHED_EVENTS", "PerformanceUpdated"]
