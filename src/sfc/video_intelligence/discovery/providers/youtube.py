"""YouTube channel footage discovery provider.

Two discovery modes (in order of richness):
1. YouTube Data API v3 — requires YOUTUBE_API_KEY; returns full metadata
2. Channel RSS feed — no key needed; limited to ~15 most-recent videos

Enable:  YOUTUBE_DISCOVERY_ENABLED=true
Config:  YOUTUBE_CHANNEL_IDS=UC...,UC...   (comma-separated)
         YOUTUBE_API_KEY=...               (optional; enables mode 1)
         YOUTUBE_RIGHTS_STATUS=unknown     (override rights for all assets)
         YOUTUBE_MAX_RESULTS=50            (API mode; default 50, max 50)
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from sfc.video_intelligence.discovery.models import (
    DiscoveredAsset,
    DiscoverySourceType,
    DiscoveryStatus,
)
from sfc.video_intelligence.discovery.providers.base import FootageProvider

logger = logging.getLogger("sfc.video_intelligence.discovery.youtube")

_CHANNEL_RSS_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
_YT_API_SEARCH = "https://www.googleapis.com/youtube/v3/search"
_YT_API_VIDEOS = "https://www.googleapis.com/youtube/v3/videos"


class YouTubeChannelProvider(FootageProvider):

    @property
    def name(self) -> str:
        return "youtube_channel"

    @property
    def source_type(self) -> DiscoverySourceType:
        return DiscoverySourceType.YOUTUBE_CHANNEL

    @property
    def is_enabled(self) -> bool:
        return (
            os.environ.get("YOUTUBE_DISCOVERY_ENABLED", "false").lower() == "true"
            and bool(os.environ.get("YOUTUBE_CHANNEL_IDS", "").strip())
        )

    def _channel_ids(self) -> list[str]:
        raw = os.environ.get("YOUTUBE_CHANNEL_IDS", "")
        return [c.strip() for c in raw.split(",") if c.strip()]

    def _api_key(self) -> str:
        return os.environ.get("YOUTUBE_API_KEY", "")

    def _rights_status(self) -> str:
        return os.environ.get("YOUTUBE_RIGHTS_STATUS", "unknown")

    def _max_results(self) -> int:
        try:
            return min(int(os.environ.get("YOUTUBE_MAX_RESULTS", "50")), 50)
        except ValueError:
            return 50

    async def discover(self) -> list[DiscoveredAsset]:
        if not self.is_enabled:
            return []
        assets: list[DiscoveredAsset] = []
        api_key = self._api_key()
        for channel_id in self._channel_ids():
            try:
                if api_key:
                    found = await self._discover_via_api(channel_id, api_key)
                else:
                    found = await self._discover_via_rss(channel_id)
                assets.extend(found)
                logger.info(
                    "[YouTubeProvider] channel=%s found=%d", channel_id, len(found)
                )
            except Exception as exc:
                logger.warning(
                    "[YouTubeProvider] channel=%s error: %s", channel_id, exc
                )
        return assets

    async def _discover_via_rss(self, channel_id: str) -> list[DiscoveredAsset]:
        try:
            import feedparser
        except ImportError:
            logger.warning("[YouTubeProvider] feedparser not installed")
            return []

        feed_url = _CHANNEL_RSS_URL.format(channel_id=channel_id)
        feed = feedparser.parse(feed_url)
        assets: list[DiscoveredAsset] = []
        channel_name = feed.feed.get("title", "")

        for entry in feed.entries:
            video_id = entry.get("yt_videoid", "")
            if not video_id:
                continue
            url = f"https://www.youtube.com/watch?v={video_id}"
            title = entry.get("title", "").strip()
            published = None
            if entry.get("published_parsed"):
                try:
                    import calendar
                    ts = calendar.timegm(entry.published_parsed)
                    published = datetime.fromtimestamp(ts, tz=timezone.utc)
                except Exception:
                    pass
            thumbnail_url = ""
            for thumb in entry.get("media_thumbnail", []):
                thumbnail_url = thumb.get("url", "")
                break

            assets.append(
                DiscoveredAsset(
                    title=title or url,
                    url=url,
                    source_type=self.source_type.value,
                    rights_status=self._rights_status(),
                    thumbnail_url=thumbnail_url,
                    channel_name=channel_name,
                    channel_id=channel_id,
                    published_at=published,
                    provider_name=self.name,
                    status=DiscoveryStatus.PENDING,
                    metadata={"video_id": video_id, "mode": "rss"},
                )
            )
        return assets

    async def _discover_via_api(
        self, channel_id: str, api_key: str
    ) -> list[DiscoveredAsset]:
        try:
            import httpx
        except ImportError:
            logger.warning("[YouTubeProvider] httpx not installed — falling back to RSS")
            return await self._discover_via_rss(channel_id)

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                _YT_API_SEARCH,
                params={
                    "part": "snippet",
                    "channelId": channel_id,
                    "type": "video",
                    "maxResults": self._max_results(),
                    "order": "date",
                    "key": api_key,
                },
            )
            if resp.status_code != 200:
                logger.warning(
                    "[YouTubeProvider] API search HTTP %d for channel=%s",
                    resp.status_code,
                    channel_id,
                )
                return await self._discover_via_rss(channel_id)

            data = resp.json()
            items = data.get("items", [])

        assets: list[DiscoveredAsset] = []
        for item in items:
            snippet = item.get("snippet", {})
            video_id = item.get("id", {}).get("videoId", "")
            if not video_id:
                continue
            url = f"https://www.youtube.com/watch?v={video_id}"
            title = snippet.get("title", "").strip()
            published_str = snippet.get("publishedAt", "")
            published = None
            if published_str:
                try:
                    published = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
                except Exception:
                    pass
            thumbs = snippet.get("thumbnails", {})
            thumbnail_url = (
                thumbs.get("maxres", thumbs.get("high", thumbs.get("default", {}))).get("url", "")
            )
            assets.append(
                DiscoveredAsset(
                    title=title or url,
                    description=snippet.get("description", "")[:500],
                    url=url,
                    source_type=self.source_type.value,
                    rights_status=self._rights_status(),
                    thumbnail_url=thumbnail_url,
                    channel_name=snippet.get("channelTitle", ""),
                    channel_id=channel_id,
                    published_at=published,
                    provider_name=self.name,
                    status=DiscoveryStatus.PENDING,
                    metadata={"video_id": video_id, "mode": "api_v3"},
                )
            )
        return assets
