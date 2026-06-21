"""Tests for Narrative Strategy Engine."""

import pytest

from sfc.narrative.modeling.models import NarrativeInfluenceModel, NarrativeProfile, NarrativeType
from sfc.narrative.strategy.models import (
    NarrativeStrategyReport,
    StrategyAction,
    StrategyPriority,
    StrategyRecommendation,
)
from sfc.narrative.strategy.service import NarrativeStrategyEngine, get_strategy_engine


def _make_profile(**kwargs) -> NarrativeProfile:
    influence = NarrativeInfluenceModel(
        primary_drivers=[],
        amplifiers=[],
        suppressors=[],
        platform_weights={},
        influencer_impact=0.5,
        media_impact=0.5,
        organic_impact=0.5,
    )
    defaults = dict(
        title="Strategy Test",
        narrative_type=NarrativeType.PLAYER,
        description="",
        strength_score=70.0,
        momentum_score=65.0,
        sentiment_score=75.0,
        credibility_score=80.0,
        virality_potential=50.0,
        influence_model=influence,
    )
    defaults.update(kwargs)
    return NarrativeProfile(**defaults)


class TestStrategyRecommendation:
    def test_create(self):
        r = StrategyRecommendation(
            narrative_id="n_001",
            narrative_title="Amplify Test",
            action=StrategyAction.AMPLIFY,
            priority=StrategyPriority.HIGH,
            rationale="High positive sentiment",
            expected_outcome="Increased reach",
            confidence=0.85,
            effort_score=40.0,
            impact_score=80.0,
            personas_required=["broadcaster"],
            action_steps=["Publish post", "Boost"],
            success_metrics=["Reach +50%"],
            war_room_required=False,
            expires_in_hours=24,
        )
        assert r.recommendation_id != ""
        assert r.action == StrategyAction.AMPLIFY

    def test_roi_score(self):
        r = StrategyRecommendation(
            narrative_id="n",
            narrative_title="ROI",
            action=StrategyAction.MONITOR,
            priority=StrategyPriority.MEDIUM,
            rationale="",
            expected_outcome="",
            confidence=0.7,
            effort_score=40.0,
            impact_score=80.0,
            personas_required=[],
            action_steps=[],
            success_metrics=[],
            war_room_required=False,
            expires_in_hours=48,
        )
        assert r.roi_score == pytest.approx(200.0, rel=0.01)

    def test_to_dict_includes_roi(self):
        r = StrategyRecommendation(
            narrative_id="n",
            narrative_title="T",
            action=StrategyAction.COUNTER,
            priority=StrategyPriority.IMMEDIATE,
            rationale="r",
            expected_outcome="o",
            confidence=0.8,
            effort_score=50.0,
            impact_score=70.0,
            personas_required=[],
            action_steps=[],
            success_metrics=[],
            war_room_required=False,
            expires_in_hours=6,
        )
        d = r.to_dict()
        assert "roi_score" in d

    def test_to_summary(self):
        r = StrategyRecommendation(
            narrative_id="n",
            narrative_title="Summary",
            action=StrategyAction.REDIRECT,
            priority=StrategyPriority.LOW,
            rationale="r",
            expected_outcome="o",
            confidence=0.6,
            effort_score=30.0,
            impact_score=50.0,
            personas_required=[],
            action_steps=[],
            success_metrics=[],
            war_room_required=False,
            expires_in_hours=72,
        )
        s = r.to_summary()
        assert "Summary" in s


class TestNarrativeStrategyReport:
    def test_to_dict(self):
        rec = StrategyRecommendation(
            narrative_id="n",
            narrative_title="T",
            action=StrategyAction.SUPPORT,
            priority=StrategyPriority.MEDIUM,
            rationale="r",
            expected_outcome="o",
            confidence=0.7,
            effort_score=40.0,
            impact_score=60.0,
            personas_required=[],
            action_steps=[],
            success_metrics=[],
            war_room_required=False,
            expires_in_hours=24,
        )
        report = NarrativeStrategyReport(
            recommendations=[rec],
            top_recommendation=rec,
            immediate_actions=[],
            by_action_type={},
            executive_summary="Test summary",
            war_room_escalations=[],
        )
        d = report.to_dict()
        assert isinstance(d, dict)
        assert "recommendations" in d


class TestNarrativeStrategyEngine:
    @pytest.fixture
    def engine(self):
        return NarrativeStrategyEngine()

    @pytest.mark.asyncio
    async def test_recommend_basic(self, engine):
        profile = _make_profile()
        report = await engine.recommend(profile)
        assert isinstance(report, NarrativeStrategyReport)

    @pytest.mark.asyncio
    async def test_recommendations_list(self, engine):
        profile = _make_profile()
        report = await engine.recommend(profile)
        assert isinstance(report.recommendations, list)
        assert len(report.recommendations) > 0

    @pytest.mark.asyncio
    async def test_top_recommendation_set(self, engine):
        profile = _make_profile()
        report = await engine.recommend(profile)
        assert isinstance(report.top_recommendation, StrategyRecommendation)

    @pytest.mark.asyncio
    async def test_action_types_valid(self, engine):
        profile = _make_profile()
        report = await engine.recommend(profile)
        for rec in report.recommendations:
            assert rec.action in StrategyAction.__members__.values()

    @pytest.mark.asyncio
    async def test_priority_valid(self, engine):
        profile = _make_profile()
        report = await engine.recommend(profile)
        for rec in report.recommendations:
            assert rec.priority in StrategyPriority.__members__.values()

    @pytest.mark.asyncio
    async def test_high_risk_triggers_counter(self, engine):
        profile = _make_profile(
            sentiment_score=15.0,
            strength_score=85.0,
        )
        report = await engine.recommend(profile)
        actions = {r.action for r in report.recommendations}
        assert any(a in {StrategyAction.COUNTER, StrategyAction.MONITOR, StrategyAction.REDIRECT}
                   for a in actions)

    @pytest.mark.asyncio
    async def test_positive_profile_amplify(self, engine):
        profile = _make_profile(
            sentiment_score=90.0,
            strength_score=80.0,
            momentum_score=75.0,
        )
        report = await engine.recommend(profile)
        actions = {r.action for r in report.recommendations}
        assert any(a in {StrategyAction.AMPLIFY, StrategyAction.ACCELERATE, StrategyAction.SUPPORT}
                   for a in actions)

    @pytest.mark.asyncio
    async def test_executive_summary_string(self, engine):
        profile = _make_profile()
        report = await engine.recommend(profile)
        assert isinstance(report.executive_summary, str)

    def test_singleton(self):
        a = get_strategy_engine()
        b = get_strategy_engine()
        assert a is b
