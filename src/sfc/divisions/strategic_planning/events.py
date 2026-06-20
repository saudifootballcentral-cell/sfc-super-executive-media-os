"""Strategic Planning Division — event definitions."""

from __future__ import annotations

from sfc.events.types import PlanningCycleCompleted, PlanningCycleStarted

SUBSCRIBED_EVENTS: list[str] = ["performance_updated"]
PUBLISHED_EVENTS: list[str] = ["planning_cycle_started", "planning_cycle_completed"]

__all__ = [
    "SUBSCRIBED_EVENTS", "PUBLISHED_EVENTS",
    "PlanningCycleStarted", "PlanningCycleCompleted",
]
