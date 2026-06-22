"""YouTube Data API v3 provider for Package 10A."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any

from sfc.data.fixtures.loader import get_fixture_loader
from sfc.data.providers.base import BaseDataProvider

logger = logging.getLogger("sfc.data.providers.youtube")

_CHANNEL_URL = "https://www.googleapis.com/youtube/v3/channels"
_VIDEO_URL = "https://www.googleapis.com/youtube/v3/videos"


class YouTubeDataProvider(BaseDataProvider):
    """Fetches channel and video analytics from YouTube Data API v3.
    Falls back to fixture data when credentials are absent."""

    def __init__(self) -> None:
        self._api_key = os.environ.get("YOUTUBE_API_KEY", "")
        self._channel_id = os.environ.get("YOUTUBE_CHANNEL_ID", "UCsfc_mock_channel")
        self._fixtures = get_fixture_loader()

    @property
    def data_source(self) -> str:
        return "youtube_api" if self.is_available() else "mock_fixture"

    def is_available(self) -> bool:
        return bool(self._api_key)

    async def fetch(self, query: str, **kwargs: Any) -> list[dict[str, Any]]:
        if self.is_available():
            return await self._fetch_live(query, **kwargs)
        return self._fetch_fixture(query)

    async def _fetch_live(self, query: str, **kwargs: Any) -> list[dict[str, Any]]:
        try:
            import httpx
            resource_type = kwargs.get("resource_type", "channel")
            if resource_type == "channel":
                params = {
                    "part": "statistics,snippet",
                    "id": self._channel_id,
                    "key": self._api_key,
                }
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(_CHANNEL_URL, params=params)
                    resp.raise_for_status()
                    items = resp.json().get("items", [])
                    results = []
                    for item in items:
                        stats = item.get("statistics", {})
                        results.append({
                            "subscriber_count": int(stats.get("subscriberCount", 0)),
                            "total_views": int(stats.get("viewCount", 0)),
                            "video_count": int(stats.get("videoCount", 0)),
                            "collected_at": datetime.utcnow().isoformat(),
                        })
                    logger.info("[YouTubeDataProvider] Fetched channel stats live")
                    return results
            return self._fetch_fixture(query)
        except Exception as exc:
            logger.warning("[YouTubeDataProvider] Live fetch failed (%s), falling back", exc)
            return self._fetch_fixture(query)

    def _fetch_fixture(self, query: str) -> list[dict[str, Any]]:
        q = query.lower()
        if "channel" in q:
            data = self._fixtures.get_analytics_channel()
            data.setdefault("collected_at", datetime.utcnow().isoformat())
            return [data]

        video_type = "default"
        if "short" in q:
            video_type = "short"
        elif "highlight" in q:
            video_type = "highlights_video"
        elif "report" in q or "match" in q:
            video_type = "match_report"

        data = self._fixtures.get_analytics_video(video_type)
        data.setdefault("collected_at", datetime.utcnow().isoformat())
        return [data]
