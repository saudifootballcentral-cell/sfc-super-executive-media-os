"""Buffer connector analytics — wraps BufferAnalyticsProvider with status sync."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any

from sfc.analytics_sync.providers.buffer import BufferAnalyticsProvider, get_buffer_analytics_provider

logger = logging.getLogger("sfc.connectors.buffer.analytics")


class BufferAnalyticsConnector:
    """Thin adapter between the Buffer connector and AnalyticsSync providers.

    Handles status sync: draft→queued→scheduled→publishing→published→failed→cancelled
    """

    _STATUS_MAP = {
        "draft": "draft",
        "buffer": "queued",
        "scheduled": "scheduled",
        "service_feedback_sent": "published",
        "failed": "failed",
        "canceled": "cancelled",
        "sent": "published",
    }

    def __init__(self, provider: BufferAnalyticsProvider | None = None) -> None:
        self._provider = provider or get_buffer_analytics_provider()
        self._live = os.environ.get("LIVE_PUBLISHING_ENABLED", "false").lower() == "true"

    async def sync_post_status(self, profile_id: str, platform_post_id: str) -> dict[str, Any]:
        """Fetch current status of a published post from Buffer."""
        if not self._live:
            return {"status": "scheduled", "dry_run": True, "platform_post_id": platform_post_id}
        try:
            data = await self._provider._call_api(f"updates/{platform_post_id}.json")
            raw_status = data.get("status", "buffer")
            mapped_status = self._STATUS_MAP.get(raw_status, raw_status)
            return {
                "platform_post_id": platform_post_id,
                "status": mapped_status,
                "raw_status": raw_status,
                "due_at": data.get("due_at", ""),
                "statistics": data.get("statistics", {}),
                "fetched_at": datetime.utcnow().isoformat(),
            }
        except Exception as exc:
            logger.error("[BufferAnalytics] Status sync failed for %s: %s", platform_post_id, exc)
            return {"status": "unknown", "error": str(exc)}

    async def get_post_analytics(
        self, profile_id: str, platform_post_id: str, run_id: str = ""
    ) -> dict[str, Any]:
        """Return engagement metrics for a post."""
        rec = await self._provider.fetch_post_metrics(profile_id, platform_post_id, run_id=run_id)
        return rec.to_dict()

    async def get_channel_summary(self, profile_id: str, run_id: str = "") -> dict[str, Any]:
        """Return aggregate channel performance."""
        records = await self._provider.fetch_channel_performance(profile_id, run_id=run_id)
        total_views = sum(r.views for r in records)
        total_likes = sum(r.likes for r in records)
        return {
            "profile_id": profile_id,
            "post_count": len(records),
            "total_views": total_views,
            "total_likes": total_likes,
            "run_id": run_id,
        }


_singleton: BufferAnalyticsConnector | None = None


def get_buffer_analytics_connector() -> BufferAnalyticsConnector:
    global _singleton
    if _singleton is None:
        _singleton = BufferAnalyticsConnector()
    return _singleton
