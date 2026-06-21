"""Tests for Audience Evolution Engine."""

import pytest

from sfc.audience.evolution.models import (
    AudienceEvolutionReport,
    EvolutionDriver,
    EvolutionTrend,
    GrowthForecast,
    RetentionForecast,
)
from sfc.audience.evolution.service import AudienceEvolutionEngine, get_evolution_engine


class TestEvolutionTrend:
    def test_create(self):
        t = EvolutionTrend(
            driver=EvolutionDriver.NARRATIVE_ADOPTION,
            segment_id="seg_001",
            direction="growing",
            magnitude=60.0,
            confidence=80.0,
            description="Narrative adoption driving growth",
        )
        assert t.trend_id != ""
        assert t.direction == "growing"

    def test_to_dict(self):
        t = EvolutionTrend(
            driver=EvolutionDriver.PLATFORM_MIGRATION,
            segment_id="seg_002",
            direction="declining",
            magnitude=30.0,
            confidence=70.0,
            description="Platform migration away from X",
        )
        d = t.to_dict()
        assert isinstance(d, dict)
        assert "trend_id" in d


class TestGrowthForecast:
    def test_create(self):
        f = GrowthForecast(
            segment_id="seg_001",
            segment_name="Core Fans",
            current_size=1_000_000,
            forecast_30d=1_080_000,
            forecast_90d=1_250_000,
            forecast_365d=1_800_000,
            growth_rate_monthly=8.0,
            confidence=0.85,
            key_drivers=["TikTok expansion"],
        )
        assert f.forecast_30d > f.current_size
        assert f.confidence == 0.85

    def test_to_dict(self):
        f = GrowthForecast(
            segment_id="seg",
            segment_name="Test",
            current_size=500_000,
            forecast_30d=520_000,
            forecast_90d=570_000,
            forecast_365d=700_000,
            growth_rate_monthly=4.0,
            confidence=0.75,
            key_drivers=[],
        )
        d = f.to_dict()
        assert isinstance(d, dict)
        assert "segment_id" in d


class TestRetentionForecast:
    def test_create(self):
        r = RetentionForecast(
            segment_id="seg_001",
            current_retention=80.0,
            forecast_30d_retention=79.0,
            forecast_90d_retention=77.0,
            churn_risk_score=20.0,
            at_risk_count=200_000,
            retention_actions=["Exclusive content"],
        )
        assert r.churn_risk_score == 20.0
        assert isinstance(r.retention_actions, list)

    def test_to_dict(self):
        r = RetentionForecast(
            segment_id="seg",
            current_retention=70.0,
            forecast_30d_retention=69.0,
            forecast_90d_retention=66.0,
            churn_risk_score=30.0,
            at_risk_count=150_000,
            retention_actions=[],
        )
        d = r.to_dict()
        assert isinstance(d, dict)


class TestAudienceEvolutionEngine:
    @pytest.fixture
    def engine(self):
        return AudienceEvolutionEngine()

    @pytest.mark.asyncio
    async def test_analyze_evolution(self, engine):
        report = await engine.analyze_evolution()
        assert isinstance(report, AudienceEvolutionReport)

    @pytest.mark.asyncio
    async def test_evolution_trends_list(self, engine):
        report = await engine.analyze_evolution()
        assert isinstance(report.evolution_trends, list)
        assert len(report.evolution_trends) > 0

    @pytest.mark.asyncio
    async def test_growth_forecasts_list(self, engine):
        report = await engine.analyze_evolution()
        assert isinstance(report.growth_forecasts, list)
        assert len(report.growth_forecasts) > 0

    @pytest.mark.asyncio
    async def test_retention_forecasts_list(self, engine):
        report = await engine.analyze_evolution()
        assert isinstance(report.retention_forecasts, list)
        assert len(report.retention_forecasts) > 0

    @pytest.mark.asyncio
    async def test_platform_migration_signals(self, engine):
        report = await engine.analyze_evolution()
        assert isinstance(report.platform_migration_signals, dict)

    @pytest.mark.asyncio
    async def test_x_to_tiktok_migration(self, engine):
        report = await engine.analyze_evolution()
        assert "x" in report.platform_migration_signals
        assert report.platform_migration_signals["x"] == "tiktok"

    @pytest.mark.asyncio
    async def test_total_projected_growth(self, engine):
        report = await engine.analyze_evolution()
        assert report.total_projected_growth >= 0

    @pytest.mark.asyncio
    async def test_ai_insights_string(self, engine):
        report = await engine.analyze_evolution()
        assert isinstance(report.ai_insights, str)
        assert len(report.ai_insights) > 0

    @pytest.mark.asyncio
    async def test_to_dict(self, engine):
        report = await engine.analyze_evolution()
        d = report.to_dict()
        assert isinstance(d, dict)
        assert "evolution_trends" in d

    def test_singleton(self):
        a = get_evolution_engine()
        b = get_evolution_engine()
        assert a is b

    @pytest.mark.asyncio
    async def test_with_custom_segments(self, engine):
        segments = [
            {"segment_id": f"custom_{i}", "name": f"Custom {i}", "metrics": {"size": 200_000}}
            for i in range(3)
        ]
        report = await engine.analyze_evolution(segments=segments)
        assert isinstance(report, AudienceEvolutionReport)

    @pytest.mark.asyncio
    async def test_history(self, engine):
        await engine.analyze_evolution()
        history = engine.get_history()
        assert isinstance(history, list)
        assert len(history) >= 1

    @pytest.mark.asyncio
    async def test_trend_directions_valid(self, engine):
        report = await engine.analyze_evolution()
        for t in report.evolution_trends:
            assert t.direction in ("growing", "declining")
