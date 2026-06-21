"""Tests for Audience Segmentation Engine."""

import pytest

from sfc.audience.segmentation.models import (
    AudienceCluster,
    AudienceSegment,
    AudienceSegmentReport,
    SegmentMetrics,
)
from sfc.audience.segmentation.service import AudienceSegmentationEngine, get_segmentation_engine


class TestSegmentMetrics:
    def test_create(self):
        m = SegmentMetrics(
            size=1_000_000,
            engagement_rate=15.0,
            influence_score=80.0,
            retention_rate=90.0,
            monthly_growth_rate=8.0,
            avg_session_minutes=10.0,
            content_consumption_per_day=4.0,
            churn_risk=10.0,
        )
        assert m.size == 1_000_000
        assert m.engagement_rate == 15.0


class TestAudienceSegment:
    def _make_metrics(self) -> SegmentMetrics:
        return SegmentMetrics(
            size=500_000,
            engagement_rate=12.0,
            influence_score=75.0,
            retention_rate=85.0,
            monthly_growth_rate=6.0,
            avg_session_minutes=8.0,
            content_consumption_per_day=3.5,
            churn_risk=15.0,
        )

    def test_create(self):
        s = AudienceSegment(
            cluster=AudienceCluster.HARDCORE_FANS,
            name="Hardcore Fans",
            description="Core supporter base",
            metrics=self._make_metrics(),
            primary_platforms=["x"],
            content_preferences=["highlights"],
            narrative_sensitivity={"player": 0.9},
            peak_hours=[20, 21],
            growth_opportunities=["TikTok expansion"],
            targeting_recommendations=["Prime time"],
        )
        assert s.segment_id != ""
        assert s.cluster == AudienceCluster.HARDCORE_FANS

    def test_to_dict(self):
        s = AudienceSegment(
            cluster=AudienceCluster.CASUAL_FANS,
            name="Casual",
            description="",
            metrics=self._make_metrics(),
            primary_platforms=[],
            content_preferences=[],
            narrative_sensitivity={},
            peak_hours=[],
            growth_opportunities=[],
            targeting_recommendations=[],
        )
        d = s.to_dict()
        assert isinstance(d, dict)
        assert "segment_id" in d

    def test_to_summary(self):
        s = AudienceSegment(
            cluster=AudienceCluster.NATIONAL_TEAM_FANS,
            name="National Team",
            description="",
            metrics=self._make_metrics(),
            primary_platforms=[],
            content_preferences=[],
            narrative_sensitivity={},
            peak_hours=[],
            growth_opportunities=[],
            targeting_recommendations=[],
        )
        summary = s.to_summary()
        assert isinstance(summary, str)
        assert "National Team" in summary


class TestAudienceSegmentationEngine:
    @pytest.fixture
    def engine(self):
        return AudienceSegmentationEngine()

    @pytest.mark.asyncio
    async def test_segment_all(self, engine):
        segments = await engine.segment()
        assert isinstance(segments, list)
        assert len(segments) == len(AudienceCluster)

    @pytest.mark.asyncio
    async def test_segment_subset(self, engine):
        segments = await engine.segment([AudienceCluster.HARDCORE_FANS, AudienceCluster.CASUAL_FANS])
        assert len(segments) == 2

    @pytest.mark.asyncio
    async def test_segment_sizes_positive(self, engine):
        segments = await engine.segment()
        assert all(s.metrics.size > 0 for s in segments)

    @pytest.mark.asyncio
    async def test_segment_engagement_rate_positive(self, engine):
        segments = await engine.segment()
        assert all(s.metrics.engagement_rate > 0 for s in segments)

    @pytest.mark.asyncio
    async def test_generate_report(self, engine):
        segments = await engine.segment()
        report = await engine.generate_report(segments)
        assert isinstance(report, AudienceSegmentReport)
        assert report.total_audience > 0

    @pytest.mark.asyncio
    async def test_report_fastest_growing(self, engine):
        segments = await engine.segment()
        report = await engine.generate_report(segments)
        assert report.fastest_growing in AudienceCluster.__members__.values()

    @pytest.mark.asyncio
    async def test_report_highest_engagement(self, engine):
        segments = await engine.segment()
        report = await engine.generate_report(segments)
        assert report.highest_engagement in AudienceCluster.__members__.values()

    @pytest.mark.asyncio
    async def test_report_growth_opportunities(self, engine):
        segments = await engine.segment()
        report = await engine.generate_report(segments)
        assert isinstance(report.growth_opportunities, list)

    @pytest.mark.asyncio
    async def test_get_segment(self, engine):
        segments = await engine.segment()
        sid = segments[0].segment_id
        result = engine.get_segment(sid)
        assert result is not None
        assert result.segment_id == sid

    @pytest.mark.asyncio
    async def test_get_segment_missing(self, engine):
        result = engine.get_segment("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_report_to_dict(self, engine):
        segments = await engine.segment()
        report = await engine.generate_report(segments)
        d = report.to_dict()
        assert isinstance(d, dict)
        assert "segments" in d

    def test_singleton(self):
        a = get_segmentation_engine()
        b = get_segmentation_engine()
        assert a is b

    @pytest.mark.asyncio
    async def test_history(self, engine):
        segments = await engine.segment()
        await engine.generate_report(segments)
        history = engine.get_history()
        assert isinstance(history, list)

    @pytest.mark.asyncio
    async def test_churn_risk_calculated(self, engine):
        segments = await engine.segment()
        for s in segments:
            assert 0 <= s.metrics.churn_risk <= 100
