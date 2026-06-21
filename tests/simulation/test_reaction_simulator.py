"""Tests for Public Reaction Simulator."""

import pytest

from sfc.simulation.reaction.models import (
    AudienceReactionForecast,
    MediaReaction,
    ReactionForecast,
    ReactionType,
    SimulationScenario,
    SponsorReaction,
)
from sfc.simulation.reaction.service import PublicReactionSimulator, get_reaction_simulator


class TestSimulationScenario:
    def test_all_scenarios_exist(self):
        scenarios = [s.value for s in SimulationScenario]
        assert "transfer_announcement" in scenarios
        assert "match_win" in scenarios
        assert "player_scandal" in scenarios


class TestAudienceReactionForecast:
    def _make(self, pos=60.0, neu=25.0, neg=15.0) -> AudienceReactionForecast:
        return AudienceReactionForecast(
            audience_type="core_fans",
            positive_probability=pos,
            neutral_probability=neu,
            negative_probability=neg,
            expected_engagement_multiplier=1.5,
            expected_sentiment_shift=10.0,
            controversy_probability=20.0,
        )

    def test_dominant_reaction_positive(self):
        r = self._make(pos=70.0, neu=20.0, neg=10.0)
        assert r.dominant_reaction == ReactionType.POSITIVE

    def test_dominant_reaction_negative(self):
        r = self._make(pos=15.0, neu=20.0, neg=65.0)
        assert r.dominant_reaction == ReactionType.NEGATIVE

    def test_dominant_reaction_controversial(self):
        r = AudienceReactionForecast(
            audience_type="casual_fans",
            positive_probability=30.0,
            neutral_probability=20.0,
            negative_probability=50.0,
            expected_engagement_multiplier=1.2,
            expected_sentiment_shift=-5.0,
            controversy_probability=80.0,
        )
        assert r.dominant_reaction == ReactionType.CONTROVERSIAL

    def test_to_dict_includes_dominant(self):
        r = self._make()
        d = r.to_dict()
        assert "dominant_reaction" in d

    def test_to_dict(self):
        r = self._make()
        d = r.to_dict()
        assert isinstance(d, dict)
        assert "audience_type" in d


class TestSponsorReaction:
    def test_create(self):
        s = SponsorReaction(
            sponsor_type="primary_sponsor",
            risk_level="low",
            estimated_revenue_impact=10.5,
            reputation_risk_score=5.0,
            likely_response="Positive engagement",
            mitigation_needed=False,
        )
        assert s.risk_level == "low"
        assert s.mitigation_needed is False

    def test_to_dict(self):
        s = SponsorReaction(
            sponsor_type="kit_sponsor",
            risk_level="high",
            estimated_revenue_impact=-10.0,
            reputation_risk_score=55.0,
            likely_response="Monitor",
            mitigation_needed=True,
        )
        d = s.to_dict()
        assert isinstance(d, dict)
        assert d["mitigation_needed"] is True


class TestMediaReaction:
    def test_create(self):
        m = MediaReaction(
            coverage_probability=85.0,
            tone_forecast="positive",
            amplification_factor=2.5,
            narrative_framing="Saudi football success",
            key_outlets=["Saudi Sports TV"],
        )
        assert m.tone_forecast == "positive"
        assert len(m.key_outlets) == 1

    def test_to_dict(self):
        m = MediaReaction(
            coverage_probability=70.0,
            tone_forecast="negative",
            amplification_factor=3.0,
            narrative_framing="Crisis narrative",
            key_outlets=["Al Arabiya"],
        )
        d = m.to_dict()
        assert isinstance(d, dict)


class TestReactionForecast:
    def test_to_summary(self):
        r = self._make_forecast()
        s = r.to_summary()
        assert isinstance(s, str)
        assert len(s) > 0

    def test_to_dict(self):
        r = self._make_forecast()
        d = r.to_dict()
        assert isinstance(d, dict)
        assert "forecast_id" in d

    def _make_forecast(self) -> ReactionForecast:
        audience = AudienceReactionForecast(
            audience_type="core_fans",
            positive_probability=65.0,
            neutral_probability=20.0,
            negative_probability=15.0,
            expected_engagement_multiplier=1.5,
            expected_sentiment_shift=10.0,
            controversy_probability=20.0,
        )
        sponsor = SponsorReaction(
            sponsor_type="primary",
            risk_level="low",
            estimated_revenue_impact=8.0,
            reputation_risk_score=10.0,
            likely_response="Positive",
            mitigation_needed=False,
        )
        media = MediaReaction(
            coverage_probability=80.0,
            tone_forecast="positive",
            amplification_factor=2.0,
            narrative_framing="Saudi football wins",
            key_outlets=["SPL TV"],
        )
        return ReactionForecast(
            scenario=SimulationScenario.MATCH_WIN,
            narrative_id="n_001",
            audience_reactions=[audience],
            sponsor_reaction=sponsor,
            media_reaction=media,
            overall_positive_probability=65.0,
            overall_negative_probability=15.0,
            overall_controversy_risk=20.0,
            expected_sentiment_delta=5.0,
            expected_reach_multiplier=1.65,
            risk_score=20.0,
            risk_narrative="LOW RISK",
            recommended_timing="Within 30 minutes",
            proceed_recommendation=True,
            ai_analysis="Positive reaction expected",
        )


class TestPublicReactionSimulator:
    @pytest.fixture
    def simulator(self):
        return PublicReactionSimulator()

    @pytest.mark.asyncio
    async def test_simulate_match_win(self, simulator):
        forecast = await simulator.simulate(SimulationScenario.MATCH_WIN)
        assert isinstance(forecast, ReactionForecast)
        assert forecast.scenario == SimulationScenario.MATCH_WIN

    @pytest.mark.asyncio
    async def test_simulate_player_scandal(self, simulator):
        forecast = await simulator.simulate(SimulationScenario.PLAYER_SCANDAL)
        assert forecast.risk_score > 0

    @pytest.mark.asyncio
    async def test_simulate_title_win_positive(self, simulator):
        forecast = await simulator.simulate(SimulationScenario.TITLE_WIN)
        assert forecast.overall_positive_probability > forecast.overall_negative_probability

    @pytest.mark.asyncio
    async def test_simulate_audience_reactions(self, simulator):
        forecast = await simulator.simulate(SimulationScenario.TRANSFER_ANNOUNCEMENT)
        assert isinstance(forecast.audience_reactions, list)
        assert len(forecast.audience_reactions) > 0

    @pytest.mark.asyncio
    async def test_simulate_sponsor_reaction(self, simulator):
        forecast = await simulator.simulate(SimulationScenario.SPONSORSHIP_DEAL)
        assert isinstance(forecast.sponsor_reaction, SponsorReaction)
        assert forecast.sponsor_reaction.risk_level == "low"

    @pytest.mark.asyncio
    async def test_simulate_negative_sponsor_risk(self, simulator):
        forecast = await simulator.simulate(SimulationScenario.PLAYER_SCANDAL)
        assert forecast.sponsor_reaction.risk_level == "high"

    @pytest.mark.asyncio
    async def test_simulate_media_reaction(self, simulator):
        forecast = await simulator.simulate(SimulationScenario.MATCH_LOSS)
        assert isinstance(forecast.media_reaction, MediaReaction)

    @pytest.mark.asyncio
    async def test_simulate_proceed_recommendation(self, simulator):
        forecast = await simulator.simulate(SimulationScenario.MATCH_WIN)
        assert isinstance(forecast.proceed_recommendation, bool)

    @pytest.mark.asyncio
    async def test_simulate_risk_score_range(self, simulator):
        for scenario in SimulationScenario:
            forecast = await simulator.simulate(scenario)
            assert 0 <= forecast.risk_score <= 100

    @pytest.mark.asyncio
    async def test_batch_simulate(self, simulator):
        scenarios = [SimulationScenario.MATCH_WIN, SimulationScenario.TRANSFER_ANNOUNCEMENT]
        forecasts = await simulator.batch_simulate(scenarios)
        assert len(forecasts) == 2

    @pytest.mark.asyncio
    async def test_batch_simulate_limit(self, simulator):
        scenarios = list(SimulationScenario) * 2  # 20 scenarios
        forecasts = await simulator.batch_simulate(scenarios)
        assert len(forecasts) <= 10

    @pytest.mark.asyncio
    async def test_history(self, simulator):
        await simulator.simulate(SimulationScenario.MATCH_WIN)
        history = simulator.get_history()
        assert isinstance(history, list)
        assert len(history) >= 1

    def test_singleton(self):
        a = get_reaction_simulator()
        b = get_reaction_simulator()
        assert a is b

    @pytest.mark.asyncio
    async def test_ai_analysis_string(self, simulator):
        forecast = await simulator.simulate(SimulationScenario.COACH_CHANGE)
        assert isinstance(forecast.ai_analysis, str)
        assert len(forecast.ai_analysis) > 0

    @pytest.mark.asyncio
    async def test_narrative_id_preserved(self, simulator):
        forecast = await simulator.simulate(
            SimulationScenario.TRANSFER_ANNOUNCEMENT,
            narrative_id="test_narrative_id",
        )
        assert forecast.narrative_id == "test_narrative_id"
