"""Tests for YouTube API connector (Package 9A)."""

from __future__ import annotations

import pytest

from sfc.connectors.youtube.models import (
    ChannelMetrics,
    Playlist,
    UploadStatus,
    VideoPrivacy,
    VideoUploadRequest,
    VideoPublishResult,
    YouTubeAnalytics,
    YouTubeComment,
    YouTubeConnectorReport,
)
from sfc.connectors.youtube.service import YouTubeService, get_youtube_service


class TestYouTubeModels:
    def test_upload_request_defaults(self):
        req = VideoUploadRequest(title="Test Video")
        assert req.request_id
        assert req.privacy == VideoPrivacy.PUBLIC
        assert req.language == "ar"

    def test_publish_result_to_dict(self):
        result = VideoPublishResult(video_id="abc123", title="Test")
        d = result.to_dict()
        assert d["video_id"] == "abc123"
        assert "published_at" in d

    def test_publish_result_to_summary(self):
        result = VideoPublishResult(video_id="abc", title="Match Highlights", status=UploadStatus.PUBLISHED)
        summary = result.to_summary()
        assert "PUBLISHED" in summary
        assert "abc" in summary

    def test_channel_metrics_to_dict(self):
        m = ChannelMetrics(subscriber_count=100_000, total_views=5_000_000)
        d = m.to_dict()
        assert d["subscriber_count"] == 100_000

    def test_youtube_analytics_fields(self):
        a = YouTubeAnalytics(video_id="v1", views=50000, ctr=6.5)
        assert a.views == 50000
        assert a.ctr == 6.5

    def test_playlist_to_dict(self):
        p = Playlist(title="SPL Highlights", video_ids=["v1", "v2"])
        d = p.to_dict()
        assert len(d["video_ids"]) == 2


class TestYouTubeService:
    @pytest.mark.asyncio
    async def test_upload_video(self):
        service = YouTubeService()
        req = VideoUploadRequest(title="SPL Round 10", description="Top goals")
        result = await service.upload_video(req)
        assert result.status == UploadStatus.PUBLISHED
        assert result.video_id != ""
        assert result.url.startswith("https://www.youtube.com")
        assert result.is_short is False

    @pytest.mark.asyncio
    async def test_upload_short(self):
        service = YouTubeService()
        req = VideoUploadRequest(title="Quick Reel", is_short=True)
        result = await service.upload_short(req)
        assert result.status == UploadStatus.PUBLISHED
        assert result.is_short is True

    @pytest.mark.asyncio
    async def test_update_metadata(self):
        service = YouTubeService()
        ok = await service.update_metadata("vid123", title="Updated Title")
        assert ok is True

    @pytest.mark.asyncio
    async def test_update_thumbnail(self):
        service = YouTubeService()
        ok = await service.update_thumbnail("vid123", "https://example.com/thumb.jpg")
        assert ok is True

    @pytest.mark.asyncio
    async def test_create_playlist(self):
        service = YouTubeService()
        pl = await service.create_playlist("Best Goals", video_ids=["v1", "v2", "v3"])
        assert pl.title == "Best Goals"
        assert pl.item_count == 3
        assert pl.url != ""

    @pytest.mark.asyncio
    async def test_get_analytics(self):
        service = YouTubeService()
        analytics = await service.get_analytics("vid_test")
        assert analytics.views > 0
        assert analytics.ctr > 0
        assert analytics.watch_time_hours > 0

    @pytest.mark.asyncio
    async def test_get_channel_metrics(self):
        service = YouTubeService()
        metrics = await service.get_channel_metrics()
        assert metrics.subscriber_count > 0
        assert metrics.total_views > 0

    @pytest.mark.asyncio
    async def test_get_comments(self):
        service = YouTubeService()
        comments = await service.get_comments("vid_test", max_results=5)
        assert isinstance(comments, list)
        assert len(comments) > 0
        assert all(isinstance(c, YouTubeComment) for c in comments)

    @pytest.mark.asyncio
    async def test_generate_report(self):
        service = YouTubeService()
        await service.upload_video(VideoUploadRequest(title="Video A"))
        await service.upload_short(VideoUploadRequest(title="Short A"))
        report = await service.generate_report()
        assert isinstance(report, YouTubeConnectorReport)
        assert report.videos_published >= 1
        assert report.shorts_published >= 1

    def test_observability_tracks_requests(self):
        service = YouTubeService()
        service._observability.record_success(latency_ms=100.0)
        assert service.observability.successful_requests == 1
        assert service.observability.avg_latency_ms == 100.0

    def test_not_authenticated_without_env(self):
        service = YouTubeService()
        assert service.is_authenticated is False

    def test_singleton(self):
        s1 = get_youtube_service()
        s2 = get_youtube_service()
        assert s1 is s2
