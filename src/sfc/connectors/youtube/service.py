"""YouTube API connector service — all calls mocked, credentials from env."""

from __future__ import annotations

import logging
import os
import random
from datetime import datetime
from typing import Any

from sfc.connectors.analytics.models import ConnectorObservability
from sfc.connectors.youtube.models import (
    ChannelMetrics,
    Playlist,
    UploadStatus,
    VideoPublishResult,
    VideoUploadRequest,
    YouTubeAnalytics,
    YouTubeComment,
    YouTubeConnectorReport,
)

logger = logging.getLogger("sfc.connectors.youtube")

_singleton: "YouTubeService | None" = None


def get_youtube_service() -> "YouTubeService":
    global _singleton
    if _singleton is None:
        _singleton = YouTubeService()
    return _singleton


class YouTubeService:
    """YouTube Data API v3 connector. All providers mocked; inject real
    credentials via YOUTUBE_CLIENT_ID / YOUTUBE_CLIENT_SECRET env vars."""

    _BASE_URL = "https://www.youtube.com/watch?v="

    def __init__(self) -> None:
        self._client_id = os.environ.get("YOUTUBE_CLIENT_ID", "")
        self._client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET", "")
        self._channel_id = os.environ.get("YOUTUBE_CHANNEL_ID", "UCsfc_mock_channel")
        self._observability = ConnectorObservability(connector="youtube")
        self._publish_history: list[VideoPublishResult] = []
        self._playlists: dict[str, Playlist] = {}

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    async def upload_video(self, request: VideoUploadRequest) -> VideoPublishResult:
        """Upload a regular video to YouTube."""
        return await self._upload(request, is_short=False)

    async def upload_short(self, request: VideoUploadRequest) -> VideoPublishResult:
        """Upload a YouTube Short (≤60s vertical video)."""
        return await self._upload(request, is_short=True)

    async def _upload(
        self, request: VideoUploadRequest, is_short: bool
    ) -> VideoPublishResult:
        try:
            video_id = f"yt_{request.request_id[:8]}"
            url = f"{self._BASE_URL}{video_id}"
            result = VideoPublishResult(
                request_id=request.request_id,
                video_id=video_id,
                url=url,
                status=UploadStatus.PUBLISHED,
                title=request.title,
                is_short=is_short,
                published_at=datetime.utcnow(),
            )
            self._publish_history.append(result)
            self._observability.record_success(latency_ms=random.uniform(200, 800))
            logger.info(
                "[YouTube] Uploaded %s | id=%s title=%s",
                "Short" if is_short else "Video",
                video_id,
                request.title[:40],
            )
            return result
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return VideoPublishResult(
                request_id=request.request_id,
                status=UploadStatus.FAILED,
                title=request.title,
                error_message=str(exc),
            )

    async def update_metadata(
        self,
        video_id: str,
        title: str = "",
        description: str = "",
        tags: list[str] | None = None,
    ) -> bool:
        try:
            self._observability.record_success(latency_ms=random.uniform(100, 300))
            logger.info("[YouTube] Metadata updated | id=%s", video_id)
            return True
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return False

    async def update_thumbnail(self, video_id: str, thumbnail_url: str) -> bool:
        try:
            self._observability.record_success(latency_ms=random.uniform(150, 400))
            logger.info("[YouTube] Thumbnail updated | id=%s", video_id)
            return True
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return False

    # ------------------------------------------------------------------
    # Playlists
    # ------------------------------------------------------------------

    async def create_playlist(
        self, title: str, description: str = "", video_ids: list[str] | None = None
    ) -> Playlist:
        try:
            playlist = Playlist(
                title=title,
                description=description,
                video_ids=video_ids or [],
                item_count=len(video_ids or []),
                url=f"https://www.youtube.com/playlist?list=PL_sfc_{title[:8].replace(' ','_')}",
            )
            self._playlists[playlist.playlist_id] = playlist
            self._observability.record_success(latency_ms=random.uniform(100, 200))
            logger.info("[YouTube] Playlist created | '%s' items=%d", title, playlist.item_count)
            return playlist
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return Playlist(title=title)

    async def add_to_playlist(self, playlist_id: str, video_id: str) -> bool:
        try:
            if playlist_id in self._playlists:
                self._playlists[playlist_id].video_ids.append(video_id)
                self._playlists[playlist_id].item_count += 1
            self._observability.record_success()
            return True
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return False

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    async def get_analytics(self, video_id: str) -> YouTubeAnalytics:
        try:
            analytics = YouTubeAnalytics(
                video_id=video_id,
                views=random.randint(1_000, 500_000),
                impressions=random.randint(10_000, 2_000_000),
                ctr=round(random.uniform(3.5, 12.0), 2),
                watch_time_hours=round(random.uniform(100, 50_000), 1),
                avg_view_duration_seconds=round(random.uniform(25, 180), 1),
                avg_view_percentage=round(random.uniform(30, 75), 1),
                likes=random.randint(50, 20_000),
                comments=random.randint(5, 2_000),
                shares=random.randint(10, 5_000),
                subscribers_gained=random.randint(0, 500),
            )
            self._observability.record_success(latency_ms=random.uniform(80, 250))
            return analytics
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return YouTubeAnalytics(video_id=video_id)

    async def get_channel_metrics(self) -> ChannelMetrics:
        try:
            metrics = ChannelMetrics(
                channel_id=self._channel_id,
                channel_name="SFC Saudi Football",
                subscriber_count=random.randint(50_000, 2_000_000),
                total_views=random.randint(1_000_000, 100_000_000),
                video_count=random.randint(100, 5_000),
                monthly_views=random.randint(100_000, 5_000_000),
                subscriber_growth_30d=random.randint(500, 50_000),
                avg_views_per_video=round(random.uniform(5_000, 200_000), 1),
            )
            self._observability.record_success(latency_ms=random.uniform(80, 200))
            return metrics
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return ChannelMetrics()

    async def get_comments(
        self, video_id: str, max_results: int = 20
    ) -> list[YouTubeComment]:
        try:
            sentiments = ["positive", "positive", "neutral", "positive", "negative"]
            comments: list[YouTubeComment] = []
            for i in range(min(max_results, 5)):
                comments.append(
                    YouTubeComment(
                        comment_id=f"comment_{video_id}_{i}",
                        video_id=video_id,
                        text=f"Mock comment {i+1} on video {video_id} — SFC content!",
                        author=f"@fan_{i+1}",
                        like_count=random.randint(0, 100),
                        sentiment=sentiments[i % len(sentiments)],
                    )
                )
            self._observability.record_success(latency_ms=random.uniform(100, 300))
            return comments
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return []

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    async def generate_report(self) -> YouTubeConnectorReport:
        channel = await self.get_channel_metrics()
        shorts = sum(1 for r in self._publish_history if r.is_short)
        videos = sum(1 for r in self._publish_history if not r.is_short)
        return YouTubeConnectorReport(
            videos_published=videos,
            shorts_published=shorts,
            channel_metrics=channel,
            recent_publishes=self._publish_history[-10:],
            api_errors=self._observability.api_errors,
            rate_limit_hits=self._observability.rate_limit_hits,
        )

    @property
    def observability(self) -> ConnectorObservability:
        return self._observability

    @property
    def is_authenticated(self) -> bool:
        return bool(self._client_id and self._client_secret)
