"""X (Twitter) Analytics provider — fetches tweet and account metrics."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import Any

from sfc.analytics_sync.aggregation.models import AnalyticsPlatform, ContentType, UnifiedAnalyticsRecord

logger = logging.getLogger("sfc.analytics_sync.providers.x")

_X_API_BASE = "https://api.twitter.com/2"


class XAnalyticsProvider:
    """Fetches X (Twitter) post and account analytics.

    When LIVE_PUBLISHING_ENABLED=false, returns dry-run records.
    Credentials: X_BEARER_TOKEN env var.
    """

    def __init__(self) -> None:
        self._bearer_token = os.environ.get("X_BEARER_TOKEN", "")
        self._user_id = os.environ.get("X_USER_ID", "")
        self._live = os.environ.get("LIVE_PUBLISHING_ENABLED", "false").lower() == "true"

    async def fetch_tweet_metrics(
        self,
        tweet_id: str,
        run_id: str = "",
    ) -> UnifiedAnalyticsRecord:
        """Fetch metrics for a single tweet."""
        if not self._live:
            return self._dry_run_tweet(tweet_id, run_id)
        try:
            data = await self._call_tweet_api(tweet_id)
            return self._build_tweet_record(data, tweet_id, run_id)
        except Exception as exc:
            logger.error("[XProvider] Failed to fetch tweet %s: %s", tweet_id, exc)
            return self._dry_run_tweet(tweet_id, run_id)

    async def fetch_account_metrics(self, run_id: str = "", period_days: int = 7) -> UnifiedAnalyticsRecord:
        """Fetch aggregate account metrics."""
        if not self._live:
            return self._dry_run_account(run_id)
        try:
            data = await self._call_account_api(period_days)
            return self._build_account_record(data, run_id)
        except Exception as exc:
            logger.error("[XProvider] Failed to fetch account metrics: %s", exc)
            return self._dry_run_account(run_id)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _call_tweet_api(self, tweet_id: str) -> dict[str, Any]:
        import httpx

        params = {
            "tweet.fields": "public_metrics,non_public_metrics,organic_metrics,created_at",
        }
        headers = {"Authorization": f"Bearer {self._bearer_token}"}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{_X_API_BASE}/tweets/{tweet_id}",
                params=params,
                headers=headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def _call_account_api(self, period_days: int) -> dict[str, Any]:
        import httpx

        end = datetime.utcnow()
        start = end - timedelta(days=period_days)
        params = {
            "start_time": start.isoformat() + "Z",
            "end_time": end.isoformat() + "Z",
            "granularity": "DAY",
        }
        headers = {"Authorization": f"Bearer {self._bearer_token}"}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{_X_API_BASE}/users/{self._user_id}/tweets",
                params=params,
                headers=headers,
            )
            resp.raise_for_status()
            return resp.json()

    def _build_tweet_record(self, data: dict[str, Any], tweet_id: str, run_id: str) -> UnifiedAnalyticsRecord:
        tweet_data = data.get("data", {})
        pub = tweet_data.get("public_metrics", {})
        non_pub = tweet_data.get("non_public_metrics", {})
        org = tweet_data.get("organic_metrics", {})

        impressions = non_pub.get("impression_count", org.get("impression_count", 0))
        likes = pub.get("like_count", 0)
        reposts = pub.get("retweet_count", 0)
        replies = pub.get("reply_count", 0)
        bookmarks = pub.get("bookmark_count", 0)
        profile_visits = non_pub.get("user_profile_clicks", 0)
        video_views = org.get("video_view_count", 0)

        rec = UnifiedAnalyticsRecord(
            content_id=tweet_id,
            platform=AnalyticsPlatform.X,
            content_type=ContentType.POST,
            impressions=impressions,
            views=max(impressions, video_views),
            likes=likes,
            reposts=reposts,
            replies=replies,
            bookmarks=bookmarks,
            profile_visits=profile_visits,
            run_id=run_id,
            raw=data,
        )
        rec.compute_rates()
        return rec

    def _build_account_record(self, data: dict[str, Any], run_id: str) -> UnifiedAnalyticsRecord:
        tweets = data.get("data", [])
        total_impressions = 0
        total_likes = 0
        total_replies = 0
        total_reposts = 0
        for t in tweets:
            m = t.get("public_metrics", {})
            total_likes += m.get("like_count", 0)
            total_replies += m.get("reply_count", 0)
            total_reposts += m.get("retweet_count", 0)

        rec = UnifiedAnalyticsRecord(
            content_id="account",
            platform=AnalyticsPlatform.X,
            content_type=ContentType.POST,
            impressions=total_impressions,
            views=total_impressions,
            likes=total_likes,
            replies=total_replies,
            reposts=total_reposts,
            run_id=run_id,
            raw=data,
        )
        rec.compute_rates()
        return rec

    def _dry_run_tweet(self, tweet_id: str, run_id: str) -> UnifiedAnalyticsRecord:
        rec = UnifiedAnalyticsRecord(
            content_id=tweet_id,
            platform=AnalyticsPlatform.X,
            content_type=ContentType.POST,
            views=0,
            run_id=run_id,
            raw={"dry_run": True},
        )
        rec.compute_rates()
        return rec

    def _dry_run_account(self, run_id: str) -> UnifiedAnalyticsRecord:
        rec = UnifiedAnalyticsRecord(
            content_id="account",
            platform=AnalyticsPlatform.X,
            content_type=ContentType.POST,
            views=0,
            run_id=run_id,
            raw={"dry_run": True},
        )
        rec.compute_rates()
        return rec


_singleton: XAnalyticsProvider | None = None


def get_x_analytics_provider() -> XAnalyticsProvider:
    global _singleton
    if _singleton is None:
        _singleton = XAnalyticsProvider()
    return _singleton
