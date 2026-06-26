"""Instagram Direct Graph API connector service — all calls mocked, credentials from env."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any
from uuid import uuid4

from sfc.connectors.analytics.models import ConnectorObservability
from sfc.connectors.instagram.models import (
    InstagramConnectorReport,
    InstagramInsights,
    InstagramMediaType,
    InstagramPost,
    InstagramReel,
    InstagramStory,
)

logger = logging.getLogger("sfc.connectors.instagram")

_singleton: "InstagramService | None" = None

_MEDIA_ID_BASE = 17_000_000_000_000_000


def get_instagram_service() -> "InstagramService":
    global _singleton
    if _singleton is None:
        _singleton = InstagramService()
    return _singleton


class InstagramService:
    """Instagram Graph API connector. All providers mocked; inject real credentials via
    INSTAGRAM_ACCESS_TOKEN / INSTAGRAM_BUSINESS_ACCOUNT_ID env vars."""

    def __init__(self) -> None:
        self._access_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
        self._business_account_id = os.environ.get(
            "INSTAGRAM_BUSINESS_ACCOUNT_ID", ""
        )
        self._observability = ConnectorObservability(connector="instagram")
        self._post_history: list[InstagramPost] = []
        self._reel_history: list[InstagramReel] = []
        self._story_history: list[InstagramStory] = []
        self._media_counter = 0

    def _next_media_id(self) -> str:
        self._media_counter += 1
        return str(_MEDIA_ID_BASE + self._media_counter)

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    async def create_post(self, caption: str, image_url: str) -> dict[str, Any]:
        """Create a feed post via Instagram Graph API (mocked)."""
        try:
            media_id = self._next_media_id()
            post = InstagramPost(
                platform_media_id=media_id,
                caption=caption,
                image_url=image_url,
                media_type=InstagramMediaType.IMAGE,
                permalink=f"https://www.instagram.com/p/mock_{media_id}/",
                published_at=datetime.utcnow(),
            )
            self._post_history.append(post)
            self._observability.record_success(latency_ms=420.0)
            logger.info("[Instagram] Post created | id=%s", media_id)
            return post.to_dict()
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return {"success": False, "error": str(exc)}

    async def create_reel(self, caption: str, video_url: str) -> dict[str, Any]:
        """Create a Reel via Instagram Graph API (mocked)."""
        try:
            media_id = self._next_media_id()
            reel = InstagramReel(
                platform_media_id=media_id,
                caption=caption,
                video_url=video_url,
                permalink=f"https://www.instagram.com/reel/mock_{media_id}/",
                published_at=datetime.utcnow(),
            )
            self._reel_history.append(reel)
            self._observability.record_success(latency_ms=680.0)
            logger.info("[Instagram] Reel created | id=%s", media_id)
            return reel.to_dict()
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return {"success": False, "error": str(exc)}

    async def create_story(
        self, media_url: str, media_type: str = "image"
    ) -> dict[str, Any]:
        """Create a Story via Instagram Graph API (mocked)."""
        try:
            media_id = self._next_media_id()
            story = InstagramStory(
                platform_media_id=media_id,
                media_url=media_url,
                media_type=media_type,
                published_at=datetime.utcnow(),
            )
            self._story_history.append(story)
            self._observability.record_success(latency_ms=350.0)
            logger.info("[Instagram] Story created | id=%s", media_id)
            return story.to_dict()
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return {"success": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # Insights
    # ------------------------------------------------------------------

    async def get_post_insights(self, media_id: str) -> dict[str, Any]:
        """Get insights for a specific post (mocked)."""
        try:
            insights = InstagramInsights(
                media_id=media_id,
                impressions=24_800,
                reach=18_600,
                likes=1_240,
                comments=87,
                shares=320,
                saves=540,
                engagement_rate=4.2,
            )
            self._observability.record_success(latency_ms=160.0)
            return insights.to_dict()
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return {}

    async def get_account_insights(self) -> dict[str, Any]:
        """Get account-level insights (mocked)."""
        try:
            self._observability.record_success(latency_ms=180.0)
            return {
                "account_id": self._business_account_id or "mock_ig_account",
                "followers": 128_400,
                "follows": 240,
                "media_count": 842,
                "profile_views_7d": 8_400,
                "reach_7d": 92_000,
                "impressions_7d": 184_000,
                "avg_engagement_rate": 4.1,
            }
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return {}

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    async def generate_report(self) -> InstagramConnectorReport:
        return InstagramConnectorReport(
            posts_published=len(self._post_history),
            reels_published=len(self._reel_history),
            stories_published=len(self._story_history),
            total_impressions=len(self._post_history) * 24_800,
            total_reach=len(self._post_history) * 18_600,
            api_errors=self._observability.api_errors,
            rate_limit_hits=self._observability.rate_limit_hits,
        )

    @property
    def observability(self) -> ConnectorObservability:
        return self._observability

    @property
    def is_authenticated(self) -> bool:
        return bool(self._access_token and self._business_account_id)
