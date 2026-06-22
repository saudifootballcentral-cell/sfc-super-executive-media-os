"""Tests for analytics sync service (Package 9A)."""

from __future__ import annotations

import pytest

from sfc.connectors.analytics.models import (
    AnalyticsSnapshot,
    AnalyticsSyncReport,
    ConnectorObservability,
    MetricType,
    Platform,
    PlatformGrowth,
)
from sfc.connectors.analytics.service import AnalyticsSyncService, get_analytics_sync_service


class TestAnalyticsModels:
    def test_connector_observability_record_success(self):
        obs = ConnectorObservability(connector="test")
        obs.record_success(latency_ms=150.0)
        assert obs.successful_requests == 1
        assert obs.requests_made == 1
        assert obs.avg_latency_ms == 150.0
        assert obs.success_rate == 100.0

    def test_connector_observability_record_failure(self):
        obs = ConnectorObservability(connector="test")
        obs.record_failure("timeout", rate_limited=True)
        assert obs.failed_requests == 1
        assert obs.api_errors == 1
        assert obs.rate_limit_hits == 1
        assert obs.success_rate == 0.0

    def test_success_rate_calculation(self):
        obs = ConnectorObservability(connector="test")
        obs.record_success()
        obs.record_success()
        obs.record_failure("error")
        assert abs(obs.success_rate - 66.67) < 0.1

    def test_analytics_snapshot_get_metric(self):
        snap = AnalyticsSnapshot(
            platform=Platform.YOUTUBE,
            metrics={MetricType.VIEWS.value: 50000.0, MetricType.CTR.value: 7.5},
        )
        assert snap.get(MetricType.VIEWS) == 50000.0
        assert snap.get(MetricType.CTR) == 7.5
        assert snap.get(MetricType.LIKES, 0.0) == 0.0

    def test_analytics_snapshot_to_dict(self):
        snap = AnalyticsSnapshot(platform=Platform.X, asset_id="post_1")
        d = snap.to_dict()
        assert d["platform"] == "x"
        assert "metrics" in d

    def test_analytics_sync_report_to_summary(self):
        report = AnalyticsSyncReport(
            total_views=150000,
            total_impressions=500000,
            avg_ctr=6.5,
            platforms_synced=["youtube", "x"],
        )
        summary = report.to_summary()
        assert "150,000" in summary
        assert "6.5" in summary

    def test_platform_growth_to_dict(self):
        g = PlatformGrowth(platform=Platform.INSTAGRAM, followers_or_subscribers=100_000)
        d = g.to_dict()
        assert d["platform"] == "instagram"


class TestAnalyticsSyncService:
    @pytest.mark.asyncio
    async def test_sync_youtube_analytics(self):
        service = AnalyticsSyncService()
        snaps = await service.sync_youtube_analytics(["vid1", "vid2"])
        assert len(snaps) == 2
        assert all(s.platform == Platform.YOUTUBE for s in snaps)
        assert all(s.get(MetricType.VIEWS) > 0 for s in snaps)

    @pytest.mark.asyncio
    async def test_sync_x_analytics(self):
        service = AnalyticsSyncService()
        snaps = await service.sync_x_analytics(["post1", "post2"])
        assert len(snaps) == 2
        assert all(s.platform == Platform.X for s in snaps)

    @pytest.mark.asyncio
    async def test_sync_channel_growth(self):
        service = AnalyticsSyncService()
        growth = await service.sync_channel_growth()
        assert len(growth) >= 4
        platforms = {g.platform for g in growth}
        assert Platform.YOUTUBE in platforms
        assert Platform.X in platforms

    @pytest.mark.asyncio
    async def test_sync_trend_history(self):
        service = AnalyticsSyncService()
        trends = await service.sync_trend_history()
        assert isinstance(trends, list)
        assert len(trends) > 0

    @pytest.mark.asyncio
    async def test_generate_sync_report(self):
        service = AnalyticsSyncService()
        report = await service.generate_sync_report()
        assert isinstance(report, AnalyticsSyncReport)
        assert len(report.platforms_synced) >= 2
        assert report.total_views > 0
        assert report.total_impressions > 0

    @pytest.mark.asyncio
    async def test_report_has_growth_data(self):
        service = AnalyticsSyncService()
        report = await service.generate_sync_report()
        assert len(report.platform_growth) >= 2

    @pytest.mark.asyncio
    async def test_historical_snapshots_accumulate(self):
        service = AnalyticsSyncService()
        await service.sync_youtube_analytics(["v1"])
        await service.sync_youtube_analytics(["v2"])
        history = service.get_historical_snapshots(Platform.YOUTUBE)
        assert len(history) >= 2

    @pytest.mark.asyncio
    async def test_trend_history_accumulates(self):
        service = AnalyticsSyncService()
        await service.sync_trend_history()
        history = service.get_trend_history()
        assert len(history) > 0

    def test_singleton(self):
        s1 = get_analytics_sync_service()
        s2 = get_analytics_sync_service()
        assert s1 is s2
