"""Intelligence Division — event definitions."""

from __future__ import annotations

from sfc.events.types import (
    IntelligenceBriefReady,
    OpportunityDetected,
    TrendDetected,
)

# Events this division subscribes to (triggers re-analysis)
SUBSCRIBED_EVENTS: list[str] = [
    "planning_cycle_started",
    "performance_updated",
]

# Events this division publishes
PUBLISHED_EVENTS: list[str] = [
    "intelligence_brief_ready",
    "trend_detected",
    "opportunity_detected",
]

__all__ = [
    "SUBSCRIBED_EVENTS",
    "PUBLISHED_EVENTS",
    "IntelligenceBriefReady",
    "TrendDetected",
    "OpportunityDetected",
]
