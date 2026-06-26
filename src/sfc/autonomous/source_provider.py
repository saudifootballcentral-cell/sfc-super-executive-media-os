"""Source providers for the autonomous production loop.

SourceProvider is the abstract interface; FixtureSourceProvider reads from
the saudi_news.json fixture file. RssSourceProvider fetches live RSS/Atom feeds.
SourceProviderRegistry provides a plugin architecture for registering providers.
"""

from __future__ import annotations

import abc
import logging
import os
from typing import Any

logger = logging.getLogger("sfc.autonomous.source_provider")


class SourceProvider(abc.ABC):
    """Abstract news-item source for the autonomous loop."""

    @abc.abstractmethod
    async def get_items(self) -> list[dict[str, Any]]:
        """Return news item dicts; each must have at least 'headline'."""
        ...

    @property
    @abc.abstractmethod
    def name(self) -> str: ...


class FixtureSourceProvider(SourceProvider):
    """Reads items from the saudi_news.json fixture (offline / always available)."""

    @property
    def name(self) -> str:
        return "fixture"

    async def get_items(self) -> list[dict[str, Any]]:
        from sfc.data.fixtures.loader import get_fixture_loader
        items = get_fixture_loader().get_news_items()
        logger.debug("[SourceProvider][fixture] %d items available", len(items))
        return items


class RssSourceProvider(SourceProvider):
    """Reads news items from RSS/Atom feeds using httpx (stdlib XML parsing).

    Feed URLs are taken from:
      1. feed_urls constructor argument, or
      2. RSS_FEEDS env var (comma-separated), or
      3. _DEFAULT_FEEDS class constant

    Falls back to FixtureSourceProvider if all feeds fail.
    """

    _DEFAULT_FEEDS = [
        "https://www.goal.com/ar/feeds/news",  # Arabic football news
    ]

    def __init__(self, feed_urls: list[str] | None = None) -> None:
        from_env = os.environ.get("RSS_FEEDS", "")
        env_feeds = [f.strip() for f in from_env.split(",") if f.strip()]
        self._feeds: list[str] = feed_urls or env_feeds or self._DEFAULT_FEEDS

    @property
    def name(self) -> str:
        return "rss"

    async def get_items(self) -> list[dict[str, Any]]:
        """Fetch RSS feeds and return normalized news items."""
        try:
            import httpx
        except ImportError:
            logger.warning("[RssSourceProvider] httpx not installed — falling back to fixture")
            return await FixtureSourceProvider().get_items()

        items: list[dict[str, Any]] = []
        async with httpx.AsyncClient(timeout=10.0) as client:
            for feed_url in self._feeds:
                try:
                    resp = await client.get(feed_url)
                    parsed_items = self._parse_feed(resp.text, feed_url)
                    items.extend(parsed_items)
                    logger.debug(
                        "[RssSourceProvider] Feed %s → %d items", feed_url, len(parsed_items)
                    )
                except Exception as exc:
                    logger.warning("[RssSourceProvider] Feed %s failed: %s", feed_url, exc)

        if not items:
            logger.warning("[RssSourceProvider] No items from RSS feeds — falling back to fixture")
            return await FixtureSourceProvider().get_items()

        return items

    def _parse_feed(self, xml_text: str, feed_url: str) -> list[dict[str, Any]]:
        """Parse RSS 2.0 or Atom XML and normalize to our item format."""
        import xml.etree.ElementTree as ET

        items: list[dict[str, Any]] = []
        try:
            root = ET.fromstring(xml_text)
            ns = {"atom": "http://www.w3.org/2005/Atom"}

            # --- RSS 2.0 ---
            for item in root.findall(".//item"):
                title = item.findtext("title", "").strip()
                link = item.findtext("link", "").strip()
                description = item.findtext("description", "").strip()
                pub_date = item.findtext("pubDate", "").strip()
                if title:
                    items.append({
                        "headline": title,
                        "summary": description[:500] if description else "",
                        "source_url": link,
                        "category": "news",
                        "tags": [],
                        "language": "ar",
                        "published_at": pub_date,
                        "source": feed_url,
                    })

            # --- Atom (fallback if no RSS items) ---
            if not items:
                for entry in root.findall(".//atom:entry", ns):
                    title_el = entry.find("atom:title", ns)
                    link_el = entry.find("atom:link", ns)
                    summary_el = entry.find("atom:summary", ns)
                    title = (
                        title_el.text.strip()
                        if title_el is not None and title_el.text
                        else ""
                    )
                    link = link_el.get("href", "") if link_el is not None else ""
                    summary = (
                        summary_el.text.strip()
                        if summary_el is not None and summary_el.text
                        else ""
                    )
                    if title:
                        items.append({
                            "headline": title,
                            "summary": summary[:500],
                            "source_url": link,
                            "category": "news",
                            "tags": [],
                            "language": "ar",
                            "source": feed_url,
                        })

        except ET.ParseError as exc:
            logger.warning("[RssSourceProvider] XML parse error for %s: %s", feed_url, exc)

        return items


# ---------------------------------------------------------------------------
# Plugin Registry
# ---------------------------------------------------------------------------

class SourceProviderRegistry:
    """Plugin registry for source providers.

    Add new sources without changing pipeline code — just register a provider.
    The registry aggregates items from all registered providers.
    """

    def __init__(self) -> None:
        self._providers: dict[str, SourceProvider] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        self.register("fixture", FixtureSourceProvider())
        self.register("rss", RssSourceProvider())

    def register(self, name: str, provider: SourceProvider) -> None:
        """Register a provider under the given name (replaces existing)."""
        self._providers[name] = provider
        logger.info("[SourceRegistry] Registered provider: %s", name)

    def get(self, name: str) -> SourceProvider | None:
        """Return provider by name, or None if not registered."""
        return self._providers.get(name)

    def list_providers(self) -> list[str]:
        """Return names of all registered providers."""
        return list(self._providers.keys())

    async def get_all_items(self) -> list[dict[str, Any]]:
        """Aggregate items from all registered providers, tagged with source_provider."""
        all_items: list[dict[str, Any]] = []
        for name, provider in self._providers.items():
            try:
                items = await provider.get_items()
                for item in items:
                    item.setdefault("source_provider", name)
                all_items.extend(items)
                logger.debug("[SourceRegistry] %s: %d items", name, len(items))
            except Exception as exc:
                logger.warning("[SourceRegistry] Provider %s failed: %s", name, exc)
        return all_items


# ---------------------------------------------------------------------------
# Module-level singleton registry
# ---------------------------------------------------------------------------

_registry: SourceProviderRegistry | None = None


def get_source_registry() -> SourceProviderRegistry:
    """Return the singleton SourceProviderRegistry."""
    global _registry
    if _registry is None:
        _registry = SourceProviderRegistry()
    return _registry
