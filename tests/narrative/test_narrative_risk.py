"""Tests for Narrative Risk Engine."""

import pytest

from sfc.narrative.modeling.models import NarrativeInfluenceModel, NarrativeProfile, NarrativeType
from sfc.narrative.risk.models import (
    MitigationRecommendation,
    NarrativeRiskReport,
    NarrativeRiskType,
    RiskLevel,
    RiskScore,
)
from sfc.narrative.risk.service import NarrativeRiskEngine, get_risk_engine


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
        title="Test",
        narrative_type=NarrativeType.CLUB,
        description="",
        strength_score=50.0,
        momentum_score=50.0,
        sentiment_score=50.0,
        credibility_score=70.0,
        virality_potential=30.0,
        influence_model=influence,
    )
    defaults.update(kwargs)
    return NarrativeProfile(**defaults)


class TestRiskScore:
    def test_level_critical(self):
        rs = RiskScore(
            risk_type=NarrativeRiskType.REPUTATION,
            score=85.0,
            confidence=0.9,
            trend="rising",
        )
        assert rs.level == RiskLevel.CRITICAL

    def test_level_high(self):
        rs = RiskScore(
            risk_type=NarrativeRiskType.MEDIA,
            score=65.0,
            confidence=0.8,
            trend="stable",
        )
        assert rs.level == RiskLevel.HIGH

    def test_level_medium(self):
        rs = RiskScore(
            risk_type=NarrativeRiskType.SPONSOR,
            score=50.0,
            confidence=0.7,
            trend="stable",
        )
        assert rs.level == RiskLevel.MEDIUM

    def test_level_low(self):
        rs = RiskScore(
            risk_type=NarrativeRiskType.GOVERNANCE,
            score=25.0,
            confidence=0.6,
            trend="declining",
        )
        assert rs.level == RiskLevel.LOW

    def test_to_dict_includes_level(self):
        rs = RiskScore(
            risk_type=NarrativeRiskType.FAN_BACKLASH,
            score=55.0,
            confidence=0.75,
            trend="rising",
        )
        d = rs.to_dict()
        assert "level" in d


class TestMitigationRecommendation:
    def test_create(self):
        m = MitigationRecommendation(
            risk_type=NarrativeRiskType.MISINFORMATION,
            action="Issue correction statement",
            rationale="Prevent spread",
            priority="HIGH",
            estimated_impact=70.0,
            personas_required=["spokesperson"],
            time_to_implement="2h",
        )
        assert m.recommendation_id != ""
        assert m.action == "Issue correction statement"

    def test_to_dict(self):
        m = MitigationRecommendation(
            risk_type=NarrativeRiskType.POLITICAL,
            action="Monitor closely",
            rationale="Political sensitivity",
            priority="MEDIUM",
            estimated_impact=50.0,
            personas_required=[],
            time_to_implement="24h",
        )
        d = m.to_dict()
        assert isinstance(d, dict)
        assert "recommendation_id" in d


class TestNarrativeRiskReport:
    def test_to_summary(self):
        rs = RiskScore(
            risk_type=NarrativeRiskType.REPUTATION,
            score=75.0,
            confidence=0.85,
            trend="rising",
        )
        r = NarrativeRiskReport(
            narrative_id="n_001",
            narrative_title="Risk Test",
            risk_scores=[rs],
            overall_risk_score=75.0,
            overall_risk_level=RiskLevel.HIGH,
            primary_risk=NarrativeRiskType.REPUTATION,
            mitigation_recommendations=[],
            executive_alerts=[],
            requires_war_room=False,
            ai_analysis="High risk scenario",
        )
        s = r.to_summary()
        assert "Risk Test" in s

    def test_to_dict(self):
        rs = RiskScore(
            risk_type=NarrativeRiskType.MEDIA,
            score=45.0,
            confidence=0.7,
            trend="stable",
        )
        r = NarrativeRiskReport(
            narrative_id="n_002",
            narrative_title="Dict Test",
            risk_scores=[rs],
            overall_risk_score=45.0,
            overall_risk_level=RiskLevel.MEDIUM,
            primary_risk=NarrativeRiskType.MEDIA,
            mitigation_recommendations=[],
            executive_alerts=[],
            requires_war_room=False,
            ai_analysis="Medium risk",
        )
        d = r.to_dict()
        assert d["narrative_id"] == "n_002"


class TestNarrativeRiskEngine:
    @pytest.fixture
    def engine(self):
        return NarrativeRiskEngine()

    @pytest.mark.asyncio
    async def test_assess_risk_basic(self, engine):
        profile = _make_profile()
        report = await engine.assess_risk(profile)
        assert isinstance(report, NarrativeRiskReport)
        assert report.narrative_id == profile.profile_id

    @pytest.mark.asyncio
    async def test_risk_scores_list(self, engine):
        profile = _make_profile()
        report = await engine.assess_risk(profile)
        assert isinstance(report.risk_scores, list)
        assert len(report.risk_scores) > 0

    @pytest.mark.asyncio
    async def test_overall_score_range(self, engine):
        profile = _make_profile()
        report = await engine.assess_risk(profile)
        assert 0 <= report.overall_risk_score <= 100

    @pytest.mark.asyncio
    async def test_overall_level_valid(self, engine):
        profile = _make_profile()
        report = await engine.assess_risk(profile)
        assert report.overall_risk_level in RiskLevel.__members__.values()

    @pytest.mark.asyncio
    async def test_high_risk_triggers_war_room(self, engine):
        profile = _make_profile(
            strength_score=90.0,
            sentiment_score=10.0,
            virality_potential=90.0,
            credibility_score=20.0,
        )
        report = await engine.assess_risk(profile)
        if report.overall_risk_score >= 70:
            assert report.requires_war_room is True

    @pytest.mark.asyncio
    async def test_batch_assess(self, engine):
        profiles = [_make_profile(title=f"P{i}") for i in range(3)]
        reports = await engine.batch_assess(profiles)
        assert len(reports) == 3

    @pytest.mark.asyncio
    async def test_mitigation_recommendations_list(self, engine):
        profile = _make_profile()
        report = await engine.assess_risk(profile)
        assert isinstance(report.mitigation_recommendations, list)

    def test_singleton(self):
        a = get_risk_engine()
        b = get_risk_engine()
        assert a is b

    @pytest.mark.asyncio
    async def test_ai_analysis_string(self, engine):
        profile = _make_profile()
        report = await engine.assess_risk(profile)
        assert isinstance(report.ai_analysis, str)
        assert len(report.ai_analysis) > 0
