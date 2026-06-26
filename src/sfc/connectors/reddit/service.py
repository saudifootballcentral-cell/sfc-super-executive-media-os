"""Reddit API connector service — all calls mocked, credentials from env."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any
from uuid import uuid4

from sfc.connectors.analytics.models import ConnectorObservability
from sfc.connectors.reddit.models import (
    RedditAnalytics,
    RedditConnectorReport,
    RedditPost,
    RedditPostType,
)

logger = logging.getLogger("sfc.connectors.reddit")

_singleton: "RedditService | None" = None

_FOOTBALL_SUBS = ["r/soccer", "r/SaudiFootball", "r/AlHilal", "r/AlNassr", "r/WorldCup"]


def get_reddit_service() -> "RedditService":
    global _singleton
    if _singleton is None:
        _singleton = RedditService()
    return _singleton


class RedditService:
    """Reddit API connector. All providers mocked; inject real credentials via
    REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET / REDDIT_USERNAME / REDDIT_PASSWORD env vars."""

    def __init__(self) -> None:
        self._client_id = os.environ.get("REDDIT_CLIENT_ID", "")
        self._client_secret = os.environ.get("REDDIT_CLIENT_SECRET", "")
        self._username = os.environ.get("REDDIT_USERNAME", "")
        self._password = os.environ.get("REDDIT_PASSWORD", "")
        self._observability = ConnectorObservability(connector="reddit")
        self._post_history: list[RedditPost] = []
        self._post_counter = 0

    def _next_post_id(self) -> str:
        self._post_counter += 1
        return f"t3_{uuid4().hex[:6]}"

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    async def create_post(
        self,
        subreddit: str,
        title: str,
        text: str = "",
        url: str = "",
    ) -> dict[str, Any]:
        """Create a post in a subreddit (mocked)."""
        try:
            post_id = self._next_post_id()
            post_type = RedditPostType.LINK if url else RedditPostType.TEXT
            post = RedditPost(
                platform_post_id=post_id,
                subreddit=subreddit,
                title=title,
                text=text,
                url=url,
                post_type=post_type,
                permalink=f"https://www.reddit.com/{subreddit}/comments/{post_id[3:]}/",
                published_at=datetime.utcnow(),
            )
            self._post_history.append(post)
            self._observability.record_success(latency_ms=280.0)
            logger.info(
                "[Reddit] Post created | id=%s sub=%s title=%s",
                post_id, subreddit, title[:40],
            )
            return post.to_dict()
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return {"success": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    async def get_post_analytics(self, post_id: str) -> dict[str, Any]:
        """Get analytics for a Reddit post (mocked)."""
        try:
            analytics = RedditAnalytics(
                post_id=post_id,
                upvotes=1_240,
                downvotes=86,
                score=1_154,
                upvote_ratio=0.935,
                num_comments=87,
                awards=3,
                views=12_400,
            )
            self._observability.record_success(latency_ms=120.0)
            return analytics.to_dict()
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return {}

    async def get_subreddit_trending(self, subreddit: str) -> list[dict[str, Any]]:
        """Get trending posts from a subreddit (mocked)."""
        try:
            trending = [
                {
                    "post_id": f"t3_{uuid4().hex[:6]}",
                    "subreddit": subreddit,
                    "title": f"Hot post #{i + 1} in {subreddit} — Saudi football news",
                    "score": 2_400 - i * 280,
                    "num_comments": 124 - i * 14,
                    "upvote_ratio": 0.94 - i * 0.02,
                    "permalink": f"https://www.reddit.com/{subreddit}/comments/mock_{i}/",
                }
                for i in range(5)
            ]
            self._observability.record_success(latency_ms=145.0)
            return trending
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return []

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    async def generate_report(self) -> RedditConnectorReport:
        return RedditConnectorReport(
            posts_created=len(self._post_history),
            total_upvotes=len(self._post_history) * 1_240,
            total_comments=len(self._post_history) * 87,
            api_errors=self._observability.api_errors,
            rate_limit_hits=self._observability.rate_limit_hits,
        )

    @property
    def observability(self) -> ConnectorObservability:
        return self._observability

    @property
    def is_authenticated(self) -> bool:
        return bool(
            self._client_id
            and self._client_secret
            and self._username
            and self._password
        )
