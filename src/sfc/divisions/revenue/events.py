"""Revenue Division — event definitions."""

from __future__ import annotations

from sfc.events.types import RevenueOpportunityDetected

SUBSCRIBED_EVENTS: list[str] = ["intelligence_brief_ready", "content_draft_created"]
PUBLISHED_EVENTS: list[str] = ["revenue_opportunity_detected"]

__all__ = ["SUBSCRIBED_EVENTS", "PUBLISHED_EVENTS", "RevenueOpportunityDetected"]
