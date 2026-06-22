"""Buffer Analytics provider — fetches post performance from Buffer API."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any

from sfc.analytics_sync.aggregation.models import AnalyticsPlatform, ContentType, UnifiedAnalyticsRecord

logger = logging.getLogger("sfc.analytics_sync.providers.buffer")


class BufferAnalyticsProvider:
    """Fetches Buffer post-level and channel-level analytics.

    When LIVE_PUBLISHING_ENABLED=false, returns dry-run records.
    Credentials: BUFFER_ACCESS_TOKEN env var.
    """

    def __init__(self) -> None:
        self._token = os.environ.get("BUFFER_ACCESS_TOKEN", "")
        self._live = os.environ.get("LIVE_PUBLISHING_ENABLED", "false").lower() == "true"
        self._base = "https://api.bufferapp.com/1"

    async def fetch_post_metrics(
        self,
        profile_id: str,
        post_id: str,
        run_id: str = "",
    ) -> UnifiedAnalyticsRecord:
        """Fetch analytics for a single Buffer post."""
        if not self._live:
            return self._dry_run(post_id, run_id)
        try:
            data = await self._call_api(f"profiles/{profile_id}/updates/{post_id}/interactions.json")
            return self._build_record(data, post_id, run_id)
        except Exception as exc:
            logger.error("[BufferProvider] Failed to fetch post %s: %s", post_id, exc)
            return self._dry_run(post_id, run_id)

    async def fetch_channel_performance(
        self,
        profile_id: str,
        run_id: str = "",
        count: int = 100,
    ) -> list[UnifiedAnalyticsRecord]:
        """Fetch analytics for the last N posts on a Buffer profile."""
        if not self._live:
            return []
        try:
            data = await self._call_api(f"profiles/{profile_id}/updates/sent.json", params={"count": count})
            updates = data.get("updates", [])
            records = []
            for update in updates:
                rec = self._build_record(update.get("statistics", {}), str(update.get("id", "")), run_id)
                records.append(rec)
            return records
        except Exception as exc:
            logger.error("[BufferProvider] Failed to fetch channel %s: %s", profile_id, exc)
            return []

    async def fetch_queue_performance(self, profile_id: str, run_id: str = "") -> dict[str, Any]:
        """Fetch Buffer queue stats."""
        if not self._live:
            return {"dry_run": True, "profile_id": profile_id}
        try:
            data = await self._call_api(f"profiles/{profile_id}/updates/pending.json")
            updates = data.get("updates", [])
            return {
                "profile_id": profile_id,
                "pending_count": len(updates),
                "run_id": run_id,
                "fetched_at": datetime.utcnow().isoformat(),
            }
        except Exception as exc:
            logger.error("[BufferProvider] Failed to fetch queue %s: %s", profile_id, exc)
            return {"error": str(exc)}

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _call_api(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        import httpx
        p = {"access_token": self._token}
        if params:
            p.update(params)
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{self._base}/{path}", params=p)
            resp.raise_for_status()
            return resp.json()

    def _build_record(self, stats: dict[str, Any], content_id: str, run_id: str) -> UnifiedAnalyticsRecord:
        rec = UnifiedAnalyticsRecord(
            content_id=content_id,
            platform=AnalyticsPlatform.BUFFER,
            content_type=ContentType.POST,
            views=int(stats.get("reach", 0)),
            impressions=int(stats.get("reach", 0)),
            likes=int(stats.get("likes", 0)),
            comments=int(stats.get("comments", 0)),
            shares=int(stats.get("shares", 0)),
            clicks=int(stats.get("clicks", 0)),
            run_id=run_id,
            raw=stats,
        )
        rec.compute_rates()
        return rec

    def _dry_run(self, content_id: str, run_id: str) -> UnifiedAnalyticsRecord:
        rec = UnifiedAnalyticsRecord(
            content_id=content_id,
            platform=AnalyticsPlatform.BUFFER,
            content_type=ContentType.POST,
            views=0,
            run_id=run_id,
            raw={"dry_run": True},
        )
        rec.compute_rates()
        return rec


_singleton: BufferAnalyticsProvider | None = None


def get_buffer_analytics_provider() -> BufferAnalyticsProvider:
    global _singleton
    if _singleton is None:
        _singleton = BufferAnalyticsProvider()
    return _singleton
