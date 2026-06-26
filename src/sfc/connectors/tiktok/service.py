"""TikTok Direct API connector service — all calls mocked, credentials from env."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any
from uuid import uuid4

from sfc.connectors.analytics.models import ConnectorObservability
from sfc.connectors.tiktok.models import (
    TikTokAnalytics,
    TikTokConnectorReport,
    TikTokTrend,
    TikTokVideo,
    TikTokVideoStatus,
)

logger = logging.getLogger("sfc.connectors.tiktok")

_singleton: "TikTokService | None" = None

_SAUDI_HASHTAGS = [
    "#دوري_روشن", "#الدوري_السعودي", "#كرة_القدم", "#الهلال", "#النصر",
    "#SaudiProLeague", "#SaudiFootball", "#SPL", "#AlHilal", "#AlNassr",
]


def get_tiktok_service() -> "TikTokService":
    global _singleton
    if _singleton is None:
        _singleton = TikTokService()
    return _singleton


class TikTokService:
    """TikTok Direct API connector. All providers mocked; inject real credentials via
    TIKTOK_ACCESS_TOKEN / TIKTOK_CLIENT_KEY / TIKTOK_CLIENT_SECRET env vars."""

    def __init__(self) -> None:
        self._access_token = os.environ.get("TIKTOK_ACCESS_TOKEN", "")
        self._client_key = os.environ.get("TIKTOK_CLIENT_KEY", "")
        self._client_secret = os.environ.get("TIKTOK_CLIENT_SECRET", "")
        self._observability = ConnectorObservability(connector="tiktok")
        self._video_history: list[TikTokVideo] = []
        self._video_counter = 0

    def _next_video_id(self) -> str:
        self._video_counter += 1
        return f"tt_vid_{uuid4().hex[:12]}_{self._video_counter}"

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    async def upload_video(
        self,
        video_url: str,
        title: str,
        description: str,
        hashtags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Upload a video to TikTok Direct API (mocked)."""
        try:
            video_id = self._next_video_id()
            video = TikTokVideo(
                platform_video_id=video_id,
                title=title,
                description=description,
                video_url=video_url,
                hashtags=hashtags or [],
                status=TikTokVideoStatus.PUBLISHED,
                share_url=f"https://www.tiktok.com/@sfc_football/video/{video_id}",
                published_at=datetime.utcnow(),
            )
            self._video_history.append(video)
            self._observability.record_success(latency_ms=860.0)
            logger.info("[TikTok] Video uploaded | id=%s title=%s", video_id, title[:40])
            return video.to_dict()
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return {"success": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    async def get_video_analytics(self, video_id: str) -> dict[str, Any]:
        """Get analytics for a specific TikTok video (mocked)."""
        try:
            analytics = TikTokAnalytics(
                video_id=video_id,
                views=184_000,
                likes=9_200,
                comments=640,
                shares=2_800,
                reach=142_000,
                engagement_rate=7.1,
                avg_watch_time_seconds=18.4,
                completion_rate=0.42,
            )
            self._observability.record_success(latency_ms=140.0)
            return analytics.to_dict()
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return {}

    async def get_account_analytics(self) -> dict[str, Any]:
        """Get account-level analytics (mocked)."""
        try:
            self._observability.record_success(latency_ms=160.0)
            return {
                "account": "sfc_football",
                "followers": 340_000,
                "following": 120,
                "total_likes": 8_400_000,
                "total_videos": 480,
                "profile_views_7d": 42_000,
                "video_views_7d": 1_240_000,
                "avg_engagement_rate": 7.2,
            }
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return {}

    async def get_trending_hashtags(self, location: str = "SA") -> list[dict[str, Any]]:
        """Get trending hashtags for a location (mocked)."""
        try:
            trends = [
                TikTokTrend(
                    hashtag=tag,
                    view_count=500_000 + i * 120_000,
                    video_count=8_400 + i * 1_200,
                    trend_score=95.0 - i * 8.0,
                    location=location,
                )
                for i, tag in enumerate(_SAUDI_HASHTAGS[:6])
            ]
            self._observability.record_success(latency_ms=150.0)
            return [t.to_dict() for t in trends]
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return []

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    async def generate_report(self) -> TikTokConnectorReport:
        return TikTokConnectorReport(
            videos_published=len(self._video_history),
            total_views=len(self._video_history) * 184_000,
            total_likes=len(self._video_history) * 9_200,
            api_errors=self._observability.api_errors,
            rate_limit_hits=self._observability.rate_limit_hits,
        )

    @property
    def observability(self) -> ConnectorObservability:
        return self._observability

    @property
    def is_authenticated(self) -> bool:
        return bool(self._access_token and self._client_key and self._client_secret)
