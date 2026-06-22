"""RSS/news feed provider for Package 10A via feedparser."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any

from sfc.data.fixtures.loader import get_fixture_loader
from sfc.data.providers.base import BaseDataProvider

logger = logging.getLogger("sfc.data.providers.rss")

_DEFAULT_FEEDS = [
    "https://www.arabiansports.com/feed/",
    "https://www.goal.com/feeds/en/news",
    "https://www.spl.com.sa/en/feed/",
]


class RSSProvider(BaseDataProvider):
    """Fetches news items from RSS feeds via feedparser.
    Falls back to fixture data when feedparser is unavailable or feeds are unreachable."""

    def __init__(self) -> None:
        self._enabled = os.environ.get("RSS_FEEDS_ENABLED", "").lower() == "true"
        self._feed_urls: list[str] = _DEFAULT_FEEDS
        self._fixtures = get_fixture_loader()

    @property
    def data_source(self) -> str:
        return "rss" if self.is_available() else "mock_fixture"

    def is_available(self) -> bool:
        if not self._enabled:
            return False
        try:
            import feedparser  # noqa: F401
            return True
        except ImportError:
            return False

    async def fetch(self, query: str, **kwargs: Any) -> list[dict[str, Any]]:
        if self.is_available():
            return await self._fetch_live(query, **kwargs)
        return self._fetch_fixture(query)

    async def _fetch_live(self, query: str, **kwargs: Any) -> list[dict[str, Any]]:
        try:
            import asyncio
            import feedparser
            feeds = kwargs.get("feed_urls", self._feed_urls)
            q_lower = query.lower()

            def _parse_feeds() -> list[dict[str, Any]]:
                results = []
                for url in feeds:
                    try:
                        feed = feedparser.parse(url)
                        for entry in feed.entries[:10]:
                            title = entry.get("title", "")
                            summary = entry.get("summary", "")
                            if q_lower not in title.lower() and q_lower not in summary.lower():
                                continue
                            results.append({
                                "headline": title,
                                "summary": summary,
                                "source_url": entry.get("link", ""),
                                "author": entry.get("author", ""),
                                "language": "en",
                                "tags": [t.term for t in entry.get("tags", [])],
                                "category": "news",
                                "collected_at": datetime.utcnow().isoformat(),
                            })
                    except Exception:
                        pass
                return results

            results = await asyncio.get_event_loop().run_in_executor(None, _parse_feeds)
            logger.info("[RSSProvider] Fetched %d items for '%s'", len(results), query)
            return results or self._fetch_fixture(query)
        except Exception as exc:
            logger.warning("[RSSProvider] Live fetch failed (%s), falling back", exc)
            return self._fetch_fixture(query)

    def _fetch_fixture(self, query: str) -> list[dict[str, Any]]:
        items = self._fixtures.get_news_items()
        q_lower = query.lower()
        matched = [
            i for i in items
            if q_lower in i.get("headline", "").lower()
            or q_lower in i.get("summary", "").lower()
            or any(q_lower in t.lower() for t in i.get("tags", []))
        ]
        if not matched:
            matched = items[:3]
        for item in matched:
            item.setdefault("collected_at", datetime.utcnow().isoformat())
        return matched
