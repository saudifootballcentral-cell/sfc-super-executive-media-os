"""Tests for Virality Prediction Engine."""

from __future__ import annotations

import pytest

from sfc.social.virality.models import (
    ContentFormat,
    ViralityBatch,
    ViralityForecast,
    ViralityMetrics,
    ViralityTier,
)
from sfc.social.virality.service import ViralityPredictionEngine, get_virality_engine


class TestContentFormat:
    def test_eight_formats(self):
        assert len(ContentFormat) == 8
        values = {f.value for f in ContentFormat}
        assert "short_video" in values
        assert "long_video" in values
        assert "live" in values


class TestViralityTier:
    def test_four_tiers(self):
        assert len(ViralityTier) == 4

    def test_tier_values(self):
        values = {t.value for t in ViralityTier}
        assert "viral" in values
        assert "high" in values
        assert "medium" in values
        assert "low" in values


class TestViralityMetrics:
    def test_defaults(self):
        m = ViralityMetrics()
        assert m.virality_score == 0.0
        assert m.probability == 0.0
        assert m.expected_reach == 0

    def test_tier_viral(self):
        m = ViralityMetrics(expected_reach=2_000_000)
        assert m.tier == ViralityTier.VIRAL

    def test_tier_high(self):
        m = ViralityMetrics(expected_reach=500_000)
        assert m.tier == ViralityTier.HIGH

    def test_tier_medium(self):
        m = ViralityMetrics(expected_reach=50_000)
        assert m.tier == ViralityTier.MEDIUM

    def test_tier_low(self):
        m = ViralityMetrics(expected_reach=5_000)
        assert m.tier == ViralityTier.LOW

    def test_tier_boundary_viral(self):
        m = ViralityMetrics(expected_reach=1_000_000)
        assert m.tier == ViralityTier.VIRAL

    def test_tier_boundary_high(self):
        m = ViralityMetrics(expected_reach=100_000)
        assert m.tier == ViralityTier.HIGH

    def test_tier_boundary_medium(self):
        m = ViralityMetrics(expected_reach=10_000)
        assert m.tier == ViralityTier.MEDIUM


class TestViralityForecast:
    def test_defaults(self):
        f = ViralityForecast()
        assert f.forecast_id != ""
        assert f.optimal_post_time == "18:00 UTC"
        assert f.content_format == ContentFormat.SHORT_VIDEO

    def test_to_dict(self):
        f = ViralityForecast(
            topic="Al Hilal goal",
            platform="tiktok",
            metrics=ViralityMetrics(virality_score=85.0, expected_reach=500000),
        )
        d = f.to_dict()
        assert d["topic"] == "Al Hilal goal"
        assert d["platform"] == "tiktok"

    def test_to_summary(self):
        f = ViralityForecast(
            topic="Transfer news",
            platform="x",
            metrics=ViralityMetrics(virality_score=72.0, expected_reach=200000),
        )
        s = f.to_summary()
        assert "forecast_id" in s
        assert s["topic"] == "Transfer news"
        assert s["virality_score"] == 72.0
        assert s["tier"] == "high"


class TestViralityBatch:
    def test_defaults(self):
        b = ViralityBatch()
        assert b.forecasts == []
        assert b.avg_virality_score == 0.0

    def test_to_dict(self):
        f = ViralityForecast(topic="test")
        b = ViralityBatch(forecasts=[f], avg_virality_score=65.0)
        d = b.to_dict()
        assert len(d["forecasts"]) == 1
        assert d["avg_virality_score"] == 65.0


class TestViralityPredictionEngine:
    def test_singleton(self):
        assert get_virality_engine() is get_virality_engine()

    def test_init(self):
        engine = ViralityPredictionEngine()
        assert engine._forecasts == []

    @pytest.mark.asyncio
    async def test_forecast_returns_forecast(self):
        engine = ViralityPredictionEngine()
        f = await engine.forecast(topic="Al Hilal win", platform="x")
        assert isinstance(f, ViralityForecast)
        assert f.topic == "Al Hilal win"

    @pytest.mark.asyncio
    async def test_forecast_has_valid_score(self):
        engine = ViralityPredictionEngine()
        f = await engine.forecast(topic="test topic")
        assert 0 <= f.metrics.virality_score <= 100

    @pytest.mark.asyncio
    async def test_forecast_has_optimal_time(self):
        engine = ViralityPredictionEngine()
        f = await engine.forecast(topic="match result", platform="tiktok")
        assert "UTC" in f.optimal_post_time
        assert "21:00" in f.optimal_post_time  # TikTok peak

    @pytest.mark.asyncio
    async def test_forecast_has_hashtags(self):
        engine = ViralityPredictionEngine()
        f = await engine.forecast(topic="SPL highlights")
        assert len(f.optimal_hashtags) > 0
        assert any("#" in h for h in f.optimal_hashtags)

    @pytest.mark.asyncio
    async def test_forecast_batch(self):
        engine = ViralityPredictionEngine()
        topics = ["topic1", "topic2", "topic3"]
        batch = await engine.forecast_batch(topics=topics)
        assert isinstance(batch, ViralityBatch)
        assert len(batch.forecasts) == 3

    @pytest.mark.asyncio
    async def test_batch_has_top_forecast(self):
        engine = ViralityPredictionEngine()
        batch = await engine.forecast_batch(topics=["a", "b", "c"])
        assert batch.top_forecast is not None
        assert isinstance(batch.top_forecast, ViralityForecast)

    @pytest.mark.asyncio
    async def test_batch_avg_score(self):
        engine = ViralityPredictionEngine()
        batch = await engine.forecast_batch(topics=["a", "b"])
        if batch.forecasts:
            expected = sum(f.metrics.virality_score for f in batch.forecasts) / len(batch.forecasts)
            assert batch.avg_virality_score == pytest.approx(expected, abs=0.2)

    @pytest.mark.asyncio
    async def test_get_recommendations(self):
        engine = ViralityPredictionEngine()
        recs = await engine.get_recommendations(topic="Saudi football")
        assert isinstance(recs, list)
        assert len(recs) > 0

    @pytest.mark.asyncio
    async def test_forecast_adds_to_history(self):
        engine = ViralityPredictionEngine()
        await engine.forecast(topic="history test")
        assert len(engine._forecasts) >= 1

    def test_get_history(self):
        engine = ViralityPredictionEngine()
        history = engine.get_history()
        assert isinstance(history, list)

    def test_compute_virality_score_short_video_boost(self):
        engine = ViralityPredictionEngine()
        score_video = engine._compute_virality_score(50, 0, ContentFormat.SHORT_VIDEO)
        score_long = engine._compute_virality_score(50, 0, ContentFormat.LONG_VIDEO)
        # short video has higher boost factor
        assert score_video > score_long or score_video > 0
