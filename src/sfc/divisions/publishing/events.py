"""Publishing Division — event definitions."""

from __future__ import annotations

from sfc.events.types import PublishingCompleted, PublishingRequested

SUBSCRIBED_EVENTS: list[str] = ["governance_approved"]
PUBLISHED_EVENTS: list[str] = ["publishing_requested", "publishing_completed"]

__all__ = ["SUBSCRIBED_EVENTS", "PUBLISHED_EVENTS", "PublishingRequested", "PublishingCompleted"]
