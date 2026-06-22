"""Google Trends provider for Package 10A via pytrends."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any

from sfc.data.fixtures.loader import get_fixture_loader
from sfc.data.providers.base import BaseDataProvider

logger = logging.getLogger("sfc.data.providers.google_trends")


class GoogleTrendsProvider(BaseDataProvider):
    """Fetches trend interest data via pytrends.
    Falls back to fixture data when pytrends is not installed or quota exceeded."""

    def __init__(self) -> None:
        self._enabled = os.environ.get("GOOGLE_TRENDS_ENABLED", "").lower() == "true"
        self._geo = os.environ.get("GOOGLE_TRENDS_GEO", "SA")
        self._fixtures = get_fixture_loader()

    @property
    def data_source(self) -> str:
        return "google_trends" if self.is_available() else "mock_fixture"

    def is_available(self) -> bool:
        if not self._enabled:
            return False
        try:
            import pytrends  # noqa: F401
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
            from pytrends.request import TrendReq
            timeframe = kwargs.get("timeframe", "now 7-d")

            def _sync_fetch() -> list[dict[str, Any]]:
                pt = TrendReq(hl="ar", tz=180, geo=self._geo)
                pt.build_payload([query], timeframe=timeframe, geo=self._geo)
                interest = pt.interest_over_time()
                if interest.empty:
                    return []
                avg_score = float(interest[query].mean())
                return [{
                    "term": query,
                    "tweet_volume": int(avg_score * 1000),
                    "velocity": float(interest[query].diff().mean() or 0),
                    "sentiment": "neutral",
                    "relevance_score": avg_score,
                    "category": "google_trends",
                    "collected_at": datetime.utcnow().isoformat(),
                }]

            results = await asyncio.get_event_loop().run_in_executor(None, _sync_fetch)
            logger.info("[GoogleTrendsProvider] Fetched live trends for '%s'", query)
            return results
        except Exception as exc:
            logger.warning("[GoogleTrendsProvider] Live fetch failed (%s), falling back", exc)
            return self._fetch_fixture(query)

    def _fetch_fixture(self, query: str) -> list[dict[str, Any]]:
        topic_scores = self._fixtures.get_topic_scores()
        matched_key = None
        q_lower = query.lower()
        for key in topic_scores:
            if any(w in key.lower() for w in q_lower.split()):
                matched_key = key
                break

        if matched_key:
            d = dict(topic_scores[matched_key])
            d["term"] = matched_key
            d["category"] = "google_trends"
            d.setdefault("collected_at", datetime.utcnow().isoformat())
            return [d]

        trends = self._fixtures.get_trends()
        for t in trends:
            if q_lower in t.get("term", "").lower():
                result = dict(t)
                result.setdefault("collected_at", datetime.utcnow().isoformat())
                return [result]

        if trends:
            result = dict(trends[0])
            result["term"] = query
            result.setdefault("collected_at", datetime.utcnow().isoformat())
            return [result]
        return []
