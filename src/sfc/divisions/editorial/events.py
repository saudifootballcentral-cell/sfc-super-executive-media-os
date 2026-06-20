"""Editorial Division — event definitions."""

from __future__ import annotations

from sfc.events.types import ContentDraftCreated, StoryCreated

SUBSCRIBED_EVENTS: list[str] = [
    "intelligence_brief_ready",
    "planning_cycle_started",
]

PUBLISHED_EVENTS: list[str] = [
    "content_draft_created",
    "story_created",
]

__all__ = ["SUBSCRIBED_EVENTS", "PUBLISHED_EVENTS", "ContentDraftCreated", "StoryCreated"]
