"""Tests for Opportunity Detection Engine."""

from __future__ import annotations

import pytest

from sfc.social.opportunity.models import (
    Opportunity,
    OpportunityMetrics,
    OpportunityReport,
    OpportunityType,
)
from sfc.social.opportunity.service import OpportunityDetectionEngine, get_opportunity_engine


class TestOpportunityType:
    def test_six_types(self):
        assert len(OpportunityType) == 6
        values = {t.value for t in OpportunityType}
        assert "content" in values
        assert "narrative" in values
        assert "sponsor" in values
        assert "growth" in values
        assert "partnership" in values
        assert "audience" in values


class TestOpportunityMetrics:
    def test_defaults(self):
        m = OpportunityMetrics()
        assert m.impact == 0.0
        assert m.confidence == 0.0
        assert m.revenue_potential == 0.0

    def test_priority_score_computation(self):
        m = OpportunityMetrics(
            impact=80, confidence=70, speed=60, reach=500000, revenue_potential=50000
        )
        # impact*0.35 + confidence*0.25 + speed*0.25 + min(reach/100k, 15)
        # = 28 + 17.5 + 15 + 5 = 65.5
        expected = 80 * 0.35 + 70 * 0.25 + 60 * 0.25 + min(500000 / 100_000, 15)
        assert m.priority_score == pytest.approx(expected, abs=0.2)

    def test_priority_score_caps_reach(self):
        m = OpportunityMetrics(
            impact=0, confidence=0, speed=0, reach=10_000_000, revenue_potential=0
        )
        # reach contribution capped at 15
        assert m.priority_score == pytest.approx(15.0, abs=0.2)

    def test_priority_score_all_zero(self):
        m = OpportunityMetrics()
        assert m.priority_score == pytest.approx(0.0, abs=0.2)


class TestOpportunity:
    def test_creation(self):
        o = Opportunity(title="Breaking Content Opportunity")
        assert o.opportunity_id != ""
        assert o.title == "Breaking Content Opportunity"
        assert o.opportunity_type == OpportunityType.CONTENT

    def test_to_dict(self):
        o = Opportunity(
            title="Transfer Partnership",
            opportunity_type=OpportunityType.PARTNERSHIP,
            description="New partnership opportunity.",
        )
        d = o.to_dict()
        assert d["title"] == "Transfer Partnership"
        assert d["opportunity_type"] == "partnership"

    def test_to_summary(self):
        m = OpportunityMetrics(impact=70, confidence=80, speed=90, reach=200000)
        o = Opportunity(
            title="Growth Campaign",
            opportunity_type=OpportunityType.GROWTH,
            metrics=m,
        )
        s = o.to_summary()
        assert "opportunity_id" in s
        assert s["title"] == "Growth Campaign"
        assert s["type"] == "growth"
        assert "priority_score" in s


class TestOpportunityReport:
    def test_defaults(self):
        r = OpportunityReport()
        assert r.opportunities == []
        assert r.total_revenue_potential == 0.0
        assert r.top_opportunity is None

    def test_to_dict(self):
        r = OpportunityReport(
            executive_summary="3 high-priority opportunities detected.",
            total_revenue_potential=75000.0,
        )
        d = r.to_dict()
        assert d["total_revenue_potential"] == 75000.0
        assert d["executive_summary"] == "3 high-priority opportunities detected."


class TestOpportunityDetectionEngine:
    def test_singleton(self):
        assert get_opportunity_engine() is get_opportunity_engine()

    def test_init(self):
        engine = OpportunityDetectionEngine()
        assert engine._opportunities == []

    @pytest.mark.asyncio
    async def test_detect_with_trend_data(self):
        engine = OpportunityDetectionEngine()
        opportunities = await engine.detect(
            trend_data={"top_topic": "Al Hilal win", "top_score": 85.0}
        )
        assert isinstance(opportunities, list)

    @pytest.mark.asyncio
    async def test_detect_with_narrative_data(self):
        engine = OpportunityDetectionEngine()
        opportunities = await engine.detect(
            narrative_data={
                "top_narratives": [
                    {"title": "Transfer saga", "lifecycle": "growing"}
                ]
            }
        )
        assert isinstance(opportunities, list)

    @pytest.mark.asyncio
    async def test_detect_with_audience_data(self):
        engine = OpportunityDetectionEngine()
        opportunities = await engine.detect(
            audience_data={"total_audience": 5000000}
        )
        assert isinstance(opportunities, list)

    @pytest.mark.asyncio
    async def test_detect_sorted_by_priority(self):
        engine = OpportunityDetectionEngine()
        opportunities = await engine.detect(
            trend_data={"top_topic": "SPL highlights"},
            audience_data={"total_audience": 3000000},
        )
        scores = [o.metrics.priority_score for o in opportunities]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_generate_report_no_data(self):
        engine = OpportunityDetectionEngine()
        engine._opportunities = []
        report = await engine.generate_report()
        assert isinstance(report, OpportunityReport)

    @pytest.mark.asyncio
    async def test_generate_report_with_opportunities(self):
        engine = OpportunityDetectionEngine()
        m = OpportunityMetrics(impact=80, confidence=70, speed=90)
        opp = Opportunity(title="Test Opportunity", metrics=m)
        report = await engine.generate_report(opportunities=[opp])
        assert report.top_opportunity is not None
        assert report.top_opportunity.title == "Test Opportunity"

    @pytest.mark.asyncio
    async def test_report_total_revenue(self):
        engine = OpportunityDetectionEngine()
        opps = [
            Opportunity(
                title=f"Opp {i}",
                metrics=OpportunityMetrics(revenue_potential=10000),
            )
            for i in range(3)
        ]
        report = await engine.generate_report(opportunities=opps)
        assert report.total_revenue_potential == pytest.approx(30000.0, abs=0.1)

    @pytest.mark.asyncio
    async def test_report_by_type(self):
        engine = OpportunityDetectionEngine()
        opps = [
            Opportunity(title="Content 1", opportunity_type=OpportunityType.CONTENT),
            Opportunity(title="Content 2", opportunity_type=OpportunityType.CONTENT),
            Opportunity(title="Growth 1", opportunity_type=OpportunityType.GROWTH),
        ]
        report = await engine.generate_report(opportunities=opps)
        assert report.by_type.get("content") == 2
        assert report.by_type.get("growth") == 1

    @pytest.mark.asyncio
    async def test_report_executive_summary_not_empty(self):
        engine = OpportunityDetectionEngine()
        opps = [Opportunity(title="Opp")]
        report = await engine.generate_report(opportunities=opps)
        assert isinstance(report.executive_summary, str)
        assert len(report.executive_summary) > 0

    def test_get_history(self):
        engine = OpportunityDetectionEngine()
        history = engine.get_history()
        assert isinstance(history, list)
