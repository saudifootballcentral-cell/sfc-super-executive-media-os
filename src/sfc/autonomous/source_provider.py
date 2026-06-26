"""Source providers for the autonomous production loop.

SourceProvider is the abstract interface; FixtureSourceProvider reads from
the saudi_news.json fixture file. Future providers: RSS, matchday API, etc.
"""

from __future__ import annotations

import abc
import logging
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
