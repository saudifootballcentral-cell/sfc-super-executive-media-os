"""YouTube Analytics provider — fetches real metrics via YouTube Data/Analytics API."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import Any

from sfc.analytics_sync.aggregation.models import AnalyticsPlatform, ContentType, UnifiedAnalyticsRecord

logger = logging.getLogger("sfc.analytics_sync.providers.youtube")

_YOUTUBE_ANALYTICS_BASE = "https://youtubeanalytics.googleapis.com/v2"
_YOUTUBE_DATA_BASE = "https://www.googleapis.com/youtube/v3"


class YouTubeAnalyticsProvider:
    """Fetches YouTube channel and video analytics.

    When LIVE_PUBLISHING_ENABLED=false, returns dry-run records.
    Credentials: YOUTUBE_API_KEY or YOUTUBE_OAUTH_TOKEN env vars.
    """

    def __init__(self) -> None:
        self._api_key = os.environ.get("YOUTUBE_API_KEY", "")
        self._oauth_token = os.environ.get("YOUTUBE_OAUTH_TOKEN", "")
        self._channel_id = os.environ.get("YOUTUBE_CHANNEL_ID", "")
        self._live = os.environ.get("LIVE_PUBLISHING_ENABLED", "false").lower() == "true"

    async def fetch_video_metrics(
        self,
        video_id: str,
        run_id: str = "",
        period_days: int = 7,
    ) -> UnifiedAnalyticsRecord:
        """Fetch metrics for a single video. Returns dry-run record if not live."""
        if not self._live:
            return self._dry_run_video(video_id, run_id)
        try:
            import httpx
            data = await self._call_analytics_api(video_id, period_days)
            return self._build_record(data, video_id, run_id)
        except Exception as exc:
            logger.error("[YouTubeProvider] Failed to fetch video %s: %s", video_id, exc)
            return self._dry_run_video(video_id, run_id)

    async def fetch_channel_metrics(self, run_id: str = "", period_days: int = 7) -> UnifiedAnalyticsRecord:
        """Fetch aggregate channel metrics."""
        if not self._live:
            return self._dry_run_channel(run_id)
        try:
            data = await self._call_analytics_api(None, period_days, channel_level=True)
            return self._build_record(data, "channel", run_id)
        except Exception as exc:
            logger.error("[YouTubeProvider] Failed to fetch channel metrics: %s", exc)
            return self._dry_run_channel(run_id)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _call_analytics_api(
        self, video_id: str | None, period_days: int, channel_level: bool = False
    ) -> dict[str, Any]:
        import httpx

        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=period_days)

        params: dict[str, Any] = {
            "ids": f"channel=={self._channel_id}",
            "startDate": str(start_date),
            "endDate": str(end_date),
            "metrics": "views,likes,comments,shares,estimatedMinutesWatched,averageViewDuration,subscribersGained,annotationClickThroughRate",
            "access_token": self._oauth_token,
        }
        if video_id and not channel_level:
            params["filters"] = f"video=={video_id}"

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{_YOUTUBE_ANALYTICS_BASE}/reports", params=params)
            resp.raise_for_status()
            return resp.json()

    def _build_record(self, data: dict[str, Any], content_id: str, run_id: str) -> UnifiedAnalyticsRecord:
        rows = data.get("rows", [[]])
        row = rows[0] if rows else []
        col_headers = [c.get("name", "") for c in data.get("columnHeaders", [])]

        def _get(col: str, default: Any = 0) -> Any:
            try:
                idx = col_headers.index(col)
                return row[idx] if idx < len(row) else default
            except ValueError:
                return default

        views = int(_get("views"))
        likes = int(_get("likes"))
        comments = int(_get("comments"))
        shares = int(_get("shares"))
        watch_minutes = float(_get("estimatedMinutesWatched"))
        avg_duration = float(_get("averageViewDuration"))
        subs_gained = int(_get("subscribersGained"))

        rec = UnifiedAnalyticsRecord(
            content_id=content_id,
            platform=AnalyticsPlatform.YOUTUBE,
            content_type=ContentType.VIDEO,
            views=views,
            likes=likes,
            comments=comments,
            shares=shares,
            watch_time_seconds=watch_minutes * 60,
            avg_view_duration_seconds=avg_duration,
            subscribers_gained=subs_gained,
            run_id=run_id,
            raw=data,
        )
        rec.compute_rates()
        return rec

    def _dry_run_video(self, video_id: str, run_id: str) -> UnifiedAnalyticsRecord:
        rec = UnifiedAnalyticsRecord(
            content_id=video_id,
            platform=AnalyticsPlatform.YOUTUBE,
            content_type=ContentType.VIDEO,
            views=0,
            likes=0,
            comments=0,
            shares=0,
            run_id=run_id,
            raw={"dry_run": True},
        )
        rec.compute_rates()
        return rec

    def _dry_run_channel(self, run_id: str) -> UnifiedAnalyticsRecord:
        rec = UnifiedAnalyticsRecord(
            content_id="channel",
            platform=AnalyticsPlatform.YOUTUBE,
            content_type=ContentType.VIDEO,
            views=0,
            run_id=run_id,
            raw={"dry_run": True},
        )
        rec.compute_rates()
        return rec


_singleton: YouTubeAnalyticsProvider | None = None


def get_youtube_analytics_provider() -> YouTubeAnalyticsProvider:
    global _singleton
    if _singleton is None:
        _singleton = YouTubeAnalyticsProvider()
    return _singleton
