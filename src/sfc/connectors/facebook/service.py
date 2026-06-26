"""Facebook Graph API connector service — all calls mocked, credentials from env."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any
from uuid import uuid4

from sfc.connectors.analytics.models import ConnectorObservability
from sfc.connectors.facebook.models import (
    FacebookConnectorReport,
    FacebookInsights,
    FacebookPost,
)

logger = logging.getLogger("sfc.connectors.facebook")

_singleton: "FacebookService | None" = None

_POST_ID_BASE = 100_000_000_000_000


def get_facebook_service() -> "FacebookService":
    global _singleton
    if _singleton is None:
        _singleton = FacebookService()
    return _singleton


class FacebookService:
    """Facebook Graph API connector. All providers mocked; inject real credentials via
    FACEBOOK_ACCESS_TOKEN / FACEBOOK_PAGE_ID env vars."""

    def __init__(self) -> None:
        self._access_token = os.environ.get("FACEBOOK_ACCESS_TOKEN", "")
        self._page_id = os.environ.get("FACEBOOK_PAGE_ID", "")
        self._observability = ConnectorObservability(connector="facebook")
        self._post_history: list[FacebookPost] = []
        self._post_counter = 0

    def _next_post_id(self) -> str:
        self._post_counter += 1
        return f"{self._page_id or 'mock_page'}_{_POST_ID_BASE + self._post_counter}"

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    async def create_post(self, message: str, link: str = "") -> dict[str, Any]:
        """Create a text (or link) post on the Facebook Page (mocked)."""
        try:
            post_id = self._next_post_id()
            post = FacebookPost(
                platform_post_id=post_id,
                message=message,
                link=link,
                post_type="link" if link else "text",
                permalink=f"https://www.facebook.com/{post_id}",
                published_at=datetime.utcnow(),
            )
            self._post_history.append(post)
            self._observability.record_success(latency_ms=300.0)
            logger.info("[Facebook] Post created | id=%s", post_id)
            return post.to_dict()
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return {"success": False, "error": str(exc)}

    async def create_photo_post(
        self, message: str, photo_url: str
    ) -> dict[str, Any]:
        """Create a photo post on the Facebook Page (mocked)."""
        try:
            post_id = self._next_post_id()
            post = FacebookPost(
                platform_post_id=post_id,
                message=message,
                photo_url=photo_url,
                post_type="photo",
                permalink=f"https://www.facebook.com/{post_id}",
                published_at=datetime.utcnow(),
            )
            self._post_history.append(post)
            self._observability.record_success(latency_ms=450.0)
            logger.info("[Facebook] Photo post created | id=%s", post_id)
            return post.to_dict()
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return {"success": False, "error": str(exc)}

    async def create_video_post(
        self, message: str, video_url: str
    ) -> dict[str, Any]:
        """Create a video post on the Facebook Page (mocked)."""
        try:
            post_id = self._next_post_id()
            post = FacebookPost(
                platform_post_id=post_id,
                message=message,
                video_url=video_url,
                post_type="video",
                permalink=f"https://www.facebook.com/{post_id}",
                published_at=datetime.utcnow(),
            )
            self._post_history.append(post)
            self._observability.record_success(latency_ms=720.0)
            logger.info("[Facebook] Video post created | id=%s", post_id)
            return post.to_dict()
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return {"success": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # Insights
    # ------------------------------------------------------------------

    async def get_post_insights(self, post_id: str) -> dict[str, Any]:
        """Get insights for a specific post (mocked)."""
        try:
            insights = FacebookInsights(
                post_id=post_id,
                impressions=38_400,
                reach=22_100,
                engaged_users=1_840,
                reactions=920,
                comments=143,
                shares=287,
                link_clicks=640,
                engagement_rate=4.8,
            )
            self._observability.record_success(latency_ms=150.0)
            return insights.to_dict()
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return {}

    async def get_page_insights(self) -> dict[str, Any]:
        """Get Page-level insights (mocked)."""
        try:
            self._observability.record_success(latency_ms=170.0)
            return {
                "page_id": self._page_id or "mock_fb_page",
                "page_likes": 84_200,
                "followers": 91_400,
                "reach_7d": 280_000,
                "impressions_7d": 540_000,
                "engaged_users_7d": 18_600,
                "page_views_7d": 12_400,
                "avg_post_reach": 22_100,
            }
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return {}

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    async def generate_report(self) -> FacebookConnectorReport:
        photo_posts = sum(
            1 for p in self._post_history if p.post_type == "photo"
        )
        video_posts = sum(
            1 for p in self._post_history if p.post_type == "video"
        )
        return FacebookConnectorReport(
            posts_published=len(self._post_history),
            photo_posts_published=photo_posts,
            video_posts_published=video_posts,
            total_reach=len(self._post_history) * 22_100,
            total_impressions=len(self._post_history) * 38_400,
            api_errors=self._observability.api_errors,
            rate_limit_hits=self._observability.rate_limit_hits,
        )

    @property
    def observability(self) -> ConnectorObservability:
        return self._observability

    @property
    def is_authenticated(self) -> bool:
        return bool(self._access_token and self._page_id)
