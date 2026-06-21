"""Tests for Audience Modeling Engine."""

import pytest

from sfc.audience.modeling.models import (
    AudienceDigitalTwin,
    AudienceInfluenceModel,
    AudienceModelReport,
    AudienceType,
    BehaviorModel,
    BehaviorPattern,
    ReactionModel,
)
from sfc.audience.modeling.service import AudienceModelingEngine, get_audience_modeling_engine


class TestBehaviorModel:
    def test_create(self):
        b = BehaviorModel(
            primary_pattern=BehaviorPattern.ACTIVE_ENGAGER,
            engagement_rate=12.0,
            share_propensity=40.0,
            comment_propensity=30.0,
            narrative_adoption_speed=60.0,
            platform_loyalty=80.0,
            sentiment_volatility=25.0,
            peak_activity_hours=[20, 21, 22],
        )
        assert b.primary_pattern == BehaviorPattern.ACTIVE_ENGAGER
        assert b.engagement_rate == 12.0

    def test_peak_hours_list(self):
        b = BehaviorModel(
            primary_pattern=BehaviorPattern.PASSIVE_CONSUMER,
            engagement_rate=3.0,
            share_propensity=15.0,
            comment_propensity=10.0,
            narrative_adoption_speed=30.0,
            platform_loyalty=45.0,
            sentiment_volatility=20.0,
            peak_activity_hours=[19, 20],
        )
        assert isinstance(b.peak_activity_hours, list)


class TestReactionModel:
    def test_create(self):
        r = ReactionModel(
            positive_content_response=75.0,
            negative_content_response=20.0,
            controversy_sensitivity=35.0,
            transfer_news_response=85.0,
            match_result_response=90.0,
            player_scandal_response=60.0,
        )
        assert r.positive_content_response == 75.0


class TestAudienceInfluenceModel:
    def test_create(self):
        m = AudienceInfluenceModel(
            influenced_by=["@SPL_EN"],
            influenced_platforms=["x"],
            influence_susceptibility=50.0,
            peer_influence_weight=40.0,
            media_influence_weight=60.0,
            official_source_trust=70.0,
        )
        assert m.official_source_trust == 70.0


class TestAudienceDigitalTwin:
    def _make_twin(self, audience_type=AudienceType.FAN) -> AudienceDigitalTwin:
        behavior = BehaviorModel(
            primary_pattern=BehaviorPattern.ACTIVE_ENGAGER,
            engagement_rate=8.0,
            share_propensity=35.0,
            comment_propensity=25.0,
            narrative_adoption_speed=55.0,
            platform_loyalty=82.0,
            sentiment_volatility=20.0,
            peak_activity_hours=[20, 21],
        )
        reaction = ReactionModel(
            positive_content_response=75.0,
            negative_content_response=20.0,
            controversy_sensitivity=35.0,
            transfer_news_response=85.0,
            match_result_response=90.0,
            player_scandal_response=60.0,
        )
        influence = AudienceInfluenceModel(
            influenced_by=["@SPL_EN"],
            influenced_platforms=["x"],
            influence_susceptibility=50.0,
            peer_influence_weight=40.0,
            media_influence_weight=60.0,
            official_source_trust=70.0,
        )
        return AudienceDigitalTwin(
            audience_type=audience_type,
            name="Test Twin",
            description="Test",
            size=1_000_000,
            behavior_model=behavior,
            reaction_model=reaction,
            influence_model=influence,
            preferred_platforms=["x", "instagram"],
            preferred_content_types=["highlights"],
            top_interests=["SPL"],
            languages=["ar"],
            avg_session_minutes=10.0,
            monthly_growth_rate=5.0,
            retention_rate=80.0,
            narrative_adoption_rate=55.0,
        )

    def test_create(self):
        t = self._make_twin()
        assert t.twin_id != ""
        assert t.size == 1_000_000

    def test_to_dict(self):
        t = self._make_twin()
        d = t.to_dict()
        assert isinstance(d, dict)
        assert "twin_id" in d

    def test_to_summary(self):
        t = self._make_twin()
        s = t.to_summary()
        assert isinstance(s, str)
        assert "Test Twin" in s


class TestAudienceModelingEngine:
    @pytest.fixture
    def engine(self):
        return AudienceModelingEngine()

    @pytest.mark.asyncio
    async def test_build_models_all(self, engine):
        twins = await engine.build_models()
        assert isinstance(twins, list)
        assert len(twins) == len(AudienceType)

    @pytest.mark.asyncio
    async def test_build_models_subset(self, engine):
        twins = await engine.build_models([AudienceType.FAN, AudienceType.JOURNALIST])
        assert len(twins) == 2

    @pytest.mark.asyncio
    async def test_twin_sizes_positive(self, engine):
        twins = await engine.build_models()
        assert all(t.size > 0 for t in twins)

    @pytest.mark.asyncio
    async def test_generate_report(self, engine):
        twins = await engine.build_models()
        report = await engine.generate_report(twins)
        assert isinstance(report, AudienceModelReport)
        assert report.total_modeled_audience > 0

    @pytest.mark.asyncio
    async def test_report_dominant_type(self, engine):
        twins = await engine.build_models()
        report = await engine.generate_report(twins)
        assert report.dominant_type in AudienceType.__members__.values()

    @pytest.mark.asyncio
    async def test_report_key_insights(self, engine):
        twins = await engine.build_models()
        report = await engine.generate_report(twins)
        assert isinstance(report.key_insights, list)
        assert len(report.key_insights) > 0

    @pytest.mark.asyncio
    async def test_get_twin(self, engine):
        twins = await engine.build_models()
        tid = twins[0].twin_id
        result = engine.get_twin(tid)
        assert result is not None
        assert result.twin_id == tid

    @pytest.mark.asyncio
    async def test_get_twin_missing(self, engine):
        result = engine.get_twin("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_report_to_dict(self, engine):
        twins = await engine.build_models()
        report = await engine.generate_report(twins)
        d = report.to_dict()
        assert isinstance(d, dict)
        assert "digital_twins" in d

    def test_singleton(self):
        a = get_audience_modeling_engine()
        b = get_audience_modeling_engine()
        assert a is b

    @pytest.mark.asyncio
    async def test_history(self, engine):
        twins = await engine.build_models()
        await engine.generate_report(twins)
        history = engine.get_history()
        assert isinstance(history, list)
