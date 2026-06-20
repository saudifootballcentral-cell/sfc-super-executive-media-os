"""Creative Division — event definitions."""

from __future__ import annotations

from sfc.events.types import AssetBriefCreated, CreativeCompleted

SUBSCRIBED_EVENTS: list[str] = ["content_draft_created", "story_created"]
PUBLISHED_EVENTS: list[str] = ["creative_completed", "asset_brief_created"]

__all__ = ["SUBSCRIBED_EVENTS", "PUBLISHED_EVENTS", "AssetBriefCreated", "CreativeCompleted"]
