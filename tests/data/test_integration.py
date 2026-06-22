"""Integration tests for Package 10A — fixture-backed full scan."""

from __future__ import annotations

import pytest


class TestDataLayerIntegration:
    @pytest.mark.asyncio
    async def test_trend_radar_full_scan_produces_results(self):
        from sfc.social.trend_radar.service import TrendRadarService
        service = TrendRadarService()
        snapshot = await service.scan()
        assert snapshot.total_tracked > 0
        assert snapshot.top_topic != ""
        assert snapshot.top_score > 0

    @pytest.mark.asyncio
    async def test_sentiment_full_scan_produces_targets(self):
        from sfc.social.sentiment.service import FanSentimentService
        service = FanSentimentService()
        targets = await service.analyze()
        assert len(targets) > 0
        for t in targets:
            assert t.metrics.sample_size > 0
            assert -100 <= t.metrics.score <= 100

    @pytest.mark.asyncio
    async def test_virality_forecast_produces_meaningful_output(self):
        from sfc.social.virality.service import ViralityPredictionEngine
        from sfc.social.virality.models import ContentFormat
        engine = ViralityPredictionEngine()
        forecast = await engine.forecast(
            "Al Hilal Champions League run",
            content_format=ContentFormat.SHORT_VIDEO,
            platform="tiktok",
            trend_score=82.5,
        )
        assert forecast.metrics.virality_score > 0
        assert forecast.metrics.expected_reach > 0
        assert forecast.metrics.expected_shares > 0

    @pytest.mark.asyncio
    async def test_influencer_scan_returns_known_accounts(self):
        from sfc.social.influencer.service import InfluencerIntelligenceService
        service = InfluencerIntelligenceService()
        profiles = await service.scan()
        handles = {p.handle for p in profiles}
        assert "@AlNassrFC" in handles
        assert "@Alhilal_EN" in handles

    @pytest.mark.asyncio
    async def test_audience_analysis_total_audience_positive(self):
        from sfc.social.audience.service import AudienceIntelligenceService
        service = AudienceIntelligenceService()
        profile = await service.analyze()
        assert profile.total_audience > 1_000_000

    @pytest.mark.asyncio
    async def test_narrative_modeling_uses_fixture_scores(self):
        from sfc.narrative.modeling.service import NarrativeModelingService
        service = NarrativeModelingService()
        profiles = await service.model_narratives(
            topics=["Foreign star player signing"]
        )
        assert len(profiles) == 1
        # Fixture score for this topic is 85.2
        assert profiles[0].strength_score == pytest.approx(85.2, abs=1.0)

    @pytest.mark.asyncio
    async def test_narrative_forecasting_uses_fixture_data(self):
        from sfc.narrative.forecasting.service import NarrativeForecastingEngine
        engine = NarrativeForecastingEngine()
        forecast = await engine.forecast(
            narrative_id="test_id",
            narrative_title="Foreign star player signing",
        )
        assert forecast.overall_forecast_score > 0
        # Fixture confidence for this topic is 0.93
        assert forecast.confidence == pytest.approx(0.93, abs=0.01)

    @pytest.mark.asyncio
    async def test_youtube_channel_uses_fixture_subscriber_count(self):
        from sfc.connectors.youtube.service import YouTubeService
        service = YouTubeService()
        channel = await service.get_channel_metrics()
        # Fixture has 487000 subscribers
        assert channel.subscriber_count == 487000

    @pytest.mark.asyncio
    async def test_x_trends_use_fixture_volumes(self):
        from sfc.connectors.x.service import XService
        service = XService()
        trends = await service.get_trending_topics()
        # Check that at least one known high-volume trend is present
        volumes = {t.term: t.tweet_volume for t in trends}
        assert volumes.get("#AlHilal", 0) == 125400

    @pytest.mark.asyncio
    async def test_x_post_metrics_fixture_engagement_rate(self):
        from sfc.connectors.x.service import XService
        service = XService()
        metrics = await service.get_metrics("any_post_id")
        # Fixture default engagement_rate is 3.8
        assert metrics.engagement_rate == pytest.approx(3.8, abs=0.01)

    @pytest.mark.asyncio
    async def test_fan_pulse_report_scores_in_range(self):
        from sfc.social.sentiment.service import FanSentimentService
        service = FanSentimentService()
        report = await service.generate_fan_pulse_report()
        assert -100 <= report.overall_score <= 100
        assert len(report.tracked_entities) > 0

    @pytest.mark.asyncio
    async def test_audience_report_has_platform_breakdown(self):
        from sfc.social.audience.service import AudienceIntelligenceService
        service = AudienceIntelligenceService()
        report = await service.generate_report()
        assert len(report.platform_breakdown) > 0
        assert sum(report.platform_breakdown.values()) > 0
