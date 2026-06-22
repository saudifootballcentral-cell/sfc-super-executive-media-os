"""Tests for X API connector (Package 9A)."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from sfc.connectors.x.models import (
    XConnectorReport,
    XConversation,
    XMedia,
    XMediaType,
    XMetrics,
    XMonitorConfig,
    XPost,
    XPostStatus,
    XThread,
    XTrend,
)
from sfc.connectors.x.service import XService, get_x_service


class TestXModels:
    def test_x_post_defaults(self):
        post = XPost(text="Test post")
        assert post.post_id
        assert post.status == XPostStatus.PUBLISHED

    def test_x_post_to_dict(self):
        post = XPost(text="SPL Update", platform_post_id="123456")
        d = post.to_dict()
        assert d["text"] == "SPL Update"

    def test_x_thread_to_summary(self):
        thread = XThread(topic="Transfer News", total_posts=3)
        summary = thread.to_summary()
        assert "Transfer News" in summary
        assert "3" in summary

    def test_x_metrics_fields(self):
        m = XMetrics(views=10000, likes=500, engagement_rate=5.0)
        assert m.views == 10000
        assert m.engagement_rate == 5.0

    def test_x_trend_to_dict(self):
        t = XTrend(term="#AlHilal", tweet_volume=50000)
        d = t.to_dict()
        assert d["term"] == "#AlHilal"
        assert d["tweet_volume"] == 50000

    def test_x_monitor_config_defaults(self):
        cfg = XMonitorConfig()
        assert "ar" in cfg.languages
        assert cfg.geo == "SA"


class TestXService:
    @pytest.mark.asyncio
    async def test_create_post(self):
        service = XService()
        post = await service.create_post("SPL Round 10 results 🏆 #SaudiFootball")
        assert post.status == XPostStatus.PUBLISHED
        assert post.platform_post_id != ""
        assert post.url.startswith("https://x.com")

    @pytest.mark.asyncio
    async def test_create_post_too_long_fails(self):
        service = XService()
        long_text = "A" * 281
        post = await service.create_post(long_text)
        assert post.status == XPostStatus.FAILED

    @pytest.mark.asyncio
    async def test_create_thread(self):
        service = XService()
        thread = await service.create_thread(
            texts=["Post 1: Introduction", "Post 2: Analysis", "Post 3: Summary"],
            topic="SPL Transfer Analysis",
        )
        assert thread.status == XPostStatus.PUBLISHED
        assert thread.total_posts == 3
        assert thread.platform_thread_root_id != ""

    @pytest.mark.asyncio
    async def test_upload_media(self):
        service = XService()
        media = await service.upload_media("https://example.com/image.jpg", XMediaType.IMAGE)
        assert media.platform_media_id != ""
        assert media.media_type == XMediaType.IMAGE

    @pytest.mark.asyncio
    async def test_schedule_post(self):
        service = XService()
        future = datetime.utcnow() + timedelta(hours=2)
        post = await service.schedule_post("Scheduled test", scheduled_at=future)
        assert post.status == XPostStatus.SCHEDULED
        assert post.scheduled_at == future

    @pytest.mark.asyncio
    async def test_get_metrics(self):
        service = XService()
        metrics = await service.get_metrics("post_123")
        assert metrics.views > 0
        assert metrics.impressions > 0
        assert metrics.engagement_rate > 0

    @pytest.mark.asyncio
    async def test_search_conversations(self):
        service = XService()
        convs = await service.search_conversations("AlHilal", max_results=5)
        assert isinstance(convs, list)
        assert len(convs) > 0
        assert all(isinstance(c, XConversation) for c in convs)

    @pytest.mark.asyncio
    async def test_monitor_keywords(self):
        service = XService()
        trends = await service.monitor_keywords(["السعودي", "SPL"])
        assert isinstance(trends, list)
        assert len(trends) > 0
        assert all(isinstance(t, XTrend) for t in trends)

    @pytest.mark.asyncio
    async def test_monitor_hashtags(self):
        service = XService()
        trends = await service.monitor_hashtags(["#SaudiFootball", "#الدوري_السعودي"])
        assert len(trends) > 0

    @pytest.mark.asyncio
    async def test_get_trending_topics(self):
        service = XService()
        trends = await service.get_trending_topics()
        assert len(trends) > 0
        volumes = [t.tweet_volume for t in trends]
        assert volumes == sorted(volumes, reverse=True)

    @pytest.mark.asyncio
    async def test_generate_report(self):
        service = XService()
        await service.create_post("Post for report #SFC")
        report = await service.generate_report()
        assert isinstance(report, XConnectorReport)
        assert report.posts_published >= 1

    def test_observability_records_failure(self):
        service = XService()
        service._observability.record_failure("timeout", rate_limited=True)
        assert service.observability.api_errors == 1
        assert service.observability.rate_limit_hits == 1

    def test_not_authenticated_without_env(self):
        service = XService()
        assert service.is_authenticated is False

    def test_singleton(self):
        s1 = get_x_service()
        s2 = get_x_service()
        assert s1 is s2
