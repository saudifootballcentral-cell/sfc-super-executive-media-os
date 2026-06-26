"""RSS/Atom media feed footage discovery provider.

Parses feeds with <media:content> or <enclosure> elements that carry video files.

Enable:  RSS_MEDIA_DISCOVERY_ENABLED=true
Config:  FOOTAGE_RSS_FEEDS=https://...,...   (comma-separated feed URLs)
         RSS_MEDIA_RIGHTS_STATUS=unknown     (default rights for all assets)
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

from sfc.video_intelligence.discovery.models import (
    DiscoveredAsset,
    DiscoverySourceType,
    DiscoveryStatus,
)
from sfc.video_intelligence.discovery.providers.base import FootageProvider

logger = logging.getLogger("sfc.video_intelligence.discovery.rss_media")

_VIDEO_MIME_PREFIXES = ("video/", "application/x-mpegurl", "application/vnd.apple.mpegurl")


class RssMediaFeedProvider(FootageProvider):

    @property
    def name(self) -> str:
        return "rss_media_feed"

    @property
    def source_type(self) -> DiscoverySourceType:
        return DiscoverySourceType.RSS_MEDIA_FEED

    @property
    def is_enabled(self) -> bool:
        return (
            os.environ.get("RSS_MEDIA_DISCOVERY_ENABLED", "false").lower() == "true"
            and bool(os.environ.get("FOOTAGE_RSS_FEEDS", "").strip())
        )

    def _feed_urls(self) -> list[str]:
        raw = os.environ.get("FOOTAGE_RSS_FEEDS", "")
        return [f.strip() for f in raw.split(",") if f.strip()]

    def _rights_status(self) -> str:
        return os.environ.get("RSS_MEDIA_RIGHTS_STATUS", "unknown")

    async def discover(self) -> list[DiscoveredAsset]:
        if not self.is_enabled:
            return []
        try:
            import feedparser
        except ImportError:
            logger.warning("[RssMediaProvider] feedparser not installed")
            return []

        assets: list[DiscoveredAsset] = []
        for feed_url in self._feed_urls():
            try:
                feed = feedparser.parse(feed_url)
                found = self._extract_assets(feed, feed_url)
                assets.extend(found)
                logger.info("[RssMediaProvider] feed=%s found=%d", feed_url, len(found))
            except Exception as exc:
                logger.warning("[RssMediaProvider] feed=%s error: %s", feed_url, exc)
        return assets

    def _extract_assets(self, feed: Any, feed_url: str) -> list[DiscoveredAsset]:
        assets: list[DiscoveredAsset] = []
        channel_name = feed.feed.get("title", "")

        for entry in feed.entries:
            video_url = self._find_video_url(entry)
            if not video_url:
                continue

            title = entry.get("title", "").strip() or video_url
            published = self._parse_published(entry)
            thumbnail_url = self._find_thumbnail(entry)
            duration = self._find_duration(entry)

            assets.append(
                DiscoveredAsset(
                    title=title,
                    description=entry.get("summary", "")[:500],
                    url=video_url,
                    source_type=self.source_type.value,
                    rights_status=self._rights_status(),
                    duration_seconds=duration,
                    thumbnail_url=thumbnail_url,
                    channel_name=channel_name,
                    published_at=published,
                    provider_name=self.name,
                    status=DiscoveryStatus.PENDING,
                    metadata={"feed_url": feed_url, "entry_link": entry.get("link", "")},
                )
            )
        return assets

    def _find_video_url(self, entry: Any) -> str:
        # 1. <media:content> elements
        for mc in entry.get("media_content", []):
            url = mc.get("url", "")
            mime = mc.get("type", "")
            if url and self._is_video_mime(mime):
                return url

        # 2. <enclosure> elements (RSS 2.0)
        for enc in entry.get("enclosures", []):
            url = enc.get("href", enc.get("url", ""))
            mime = enc.get("type", "")
            if url and self._is_video_mime(mime):
                return url

        # 3. Fallback: enclosure with no type but video extension
        for enc in entry.get("enclosures", []):
            url = enc.get("href", enc.get("url", ""))
            if url and self._looks_like_video(url):
                return url

        return ""

    def _is_video_mime(self, mime: str) -> bool:
        mime = mime.lower().strip()
        return any(mime.startswith(p) for p in _VIDEO_MIME_PREFIXES)

    def _looks_like_video(self, url: str) -> bool:
        lower = url.lower().split("?")[0]
        return any(lower.endswith(ext) for ext in (".mp4", ".mov", ".avi", ".mkv", ".webm", ".m3u8"))

    def _find_thumbnail(self, entry: Any) -> str:
        for thumb in entry.get("media_thumbnail", []):
            url = thumb.get("url", "")
            if url:
                return url
        return ""

    def _find_duration(self, entry: Any) -> float:
        for mc in entry.get("media_content", []):
            dur = mc.get("duration", "")
            if dur:
                try:
                    return float(dur)
                except ValueError:
                    pass
        return 0.0

    def _parse_published(self, entry: Any) -> datetime | None:
        if entry.get("published_parsed"):
            try:
                import calendar
                ts = calendar.timegm(entry.published_parsed)
                return datetime.fromtimestamp(ts, tz=timezone.utc)
            except Exception:
                pass
        return None
