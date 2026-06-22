"""X (Twitter) API v2 data provider for Package 10A."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any

from sfc.data.fixtures.loader import get_fixture_loader
from sfc.data.providers.base import BaseDataProvider

logger = logging.getLogger("sfc.data.providers.x")

_SEARCH_URL = "https://api.twitter.com/2/tweets/search/recent"
_TRENDS_URL = "https://api.twitter.com/1.1/trends/place.json"


class XDataProvider(BaseDataProvider):
    """Fetches trend and conversation data from X API v2.
    Falls back to fixture data when credentials are absent."""

    def __init__(self) -> None:
        self._bearer_token = os.environ.get("X_BEARER_TOKEN", "")
        self._api_key = os.environ.get("X_API_KEY", "")
        self._fixtures = get_fixture_loader()

    @property
    def data_source(self) -> str:
        return "x_api" if self.is_available() else "mock_fixture"

    def is_available(self) -> bool:
        return bool(self._bearer_token or self._api_key)

    async def fetch(self, query: str, **kwargs: Any) -> list[dict[str, Any]]:
        if self.is_available():
            return await self._fetch_live(query, **kwargs)
        return self._fetch_fixture(query)

    async def _fetch_live(self, query: str, **kwargs: Any) -> list[dict[str, Any]]:
        try:
            import httpx
            headers = {"Authorization": f"Bearer {self._bearer_token}"}
            params = {
                "query": f"{query} lang:ar OR lang:en",
                "max_results": kwargs.get("max_results", 10),
                "tweet.fields": "public_metrics,created_at",
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(_SEARCH_URL, headers=headers, params=params)
                resp.raise_for_status()
                data = resp.json()
                tweets = data.get("data", [])
                results = []
                for tweet in tweets:
                    m = tweet.get("public_metrics", {})
                    results.append({
                        "term": query,
                        "tweet_volume": m.get("impression_count", 0),
                        "velocity": 0.0,
                        "sentiment": "neutral",
                        "relevance_score": 80.0,
                        "category": "live",
                        "source_url": f"https://x.com/i/status/{tweet['id']}",
                        "collected_at": datetime.utcnow().isoformat(),
                        "views": m.get("impression_count", 0),
                        "likes": m.get("like_count", 0),
                        "retweets": m.get("retweet_count", 0),
                        "replies": m.get("reply_count", 0),
                    })
                logger.info("[XDataProvider] Fetched %d tweets for '%s'", len(results), query)
                return results
        except Exception as exc:
            logger.warning("[XDataProvider] Live fetch failed (%s), falling back to fixture", exc)
            return self._fetch_fixture(query)

    def _fetch_fixture(self, query: str) -> list[dict[str, Any]]:
        trends = self._fixtures.get_trends()
        q_lower = query.lower().lstrip("#")
        matched = [
            t for t in trends
            if q_lower in t.get("term", "").lower()
            or q_lower in t.get("category", "").lower()
        ]
        if not matched:
            matched = trends[:3]
        for t in matched:
            t.setdefault("collected_at", datetime.utcnow().isoformat())
        return matched
