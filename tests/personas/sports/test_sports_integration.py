"""Integration tests for Sports Intelligence Personas."""
from __future__ import annotations

import pytest

from sfc.events.bus import get_event_bus
from sfc.personas.sports import register_sports_personas
from sfc.personas.registry.service import PersonaRegistry
from sfc.personas.sports.transfer.service import TransferPersona
from sfc.personas.sports.tactical.service import TacticalPersona
from sfc.personas.sports.national_team.service import NationalTeamPersona
from sfc.personas.sports.opponent_analysis.service import OpponentAnalysisPersona
from sfc.personas.sports.fan_sentiment.service import FanSentimentPersona
from sfc.personas.sports.journalist_intelligence.service import JournalistIntelligencePersona
from sfc.personas.sports.injury_intelligence.service import InjuryIntelligencePersona
from sfc.personas.sports.performance_science.service import PerformanceSciencePersona
from sfc.personas.sports.referee_analysis.service import RefereeAnalysisPersona


class TestSportsIntegration:
    def setup_method(self):
        get_event_bus().reset()

    async def test_register_all_sports_personas(self):
        registry = PersonaRegistry()
        count = register_sports_personas(registry)
        assert count == 13

    async def test_sports_personas_in_registry(self):
        registry = PersonaRegistry()
        register_sports_personas(registry)
        # total should be 6 seed + 13 sports
        all_personas = registry.list_all()
        assert len(all_personas) >= 13

    async def test_transfer_persona_rumor_classification(self):
        persona = TransferPersona()
        result = await persona.classify_rumor("Mohamed Salah", "Liverpool", "Al Hilal", 0.9)
        assert result["status"] == "ADVANCED_NEGOTIATION"
        result2 = await persona.classify_rumor("Player X", "Club A", "Club B", 0.3)
        assert result2["status"] == "UNCONFIRMED"

    async def test_tactical_formation_analysis(self):
        persona = TacticalPersona()
        result = await persona.analyze_formation("4-3-3", "Al Hilal")
        assert "strengths" in result
        assert len(result["strengths"]) > 0

    async def test_national_team_squad_report(self):
        persona = NationalTeamPersona()
        result = await persona.generate_squad_report(
            ["Saleh Al-Shehri", "Salem Al-Dawsari", "Mohammed Al-Owais"], "World Cup"
        )
        assert result["squad_size"] == 3
        assert "World Cup" in result["competition"]

    async def test_collaboration_transfer_journalist_sentiment(self):
        transfer = TransferPersona()
        journalist = JournalistIntelligencePersona()
        sentiment = FanSentimentPersona()
        ctx = {
            "player": "Neymar",
            "from_club": "Al Hilal",
            "to_club": "Barcelona",
            "run_id": "collab-01",
        }
        t_insight = await transfer.generate_insight(ctx)
        j_insight = await journalist.generate_insight(ctx)
        s_insight = await sentiment.generate_insight(ctx)
        combined_confidence = (
            t_insight.confidence_score
            + j_insight.confidence_score
            + s_insight.confidence_score
        ) / 3
        assert combined_confidence > 0

    async def test_match_intelligence_package(self):
        national = NationalTeamPersona()
        opponent = OpponentAnalysisPersona()
        tactical = TacticalPersona()
        ctx = {
            "team": "Saudi Arabia",
            "opponent": "Japan",
            "formation": "4-3-3",
            "competition": "Asian Cup",
        }
        n_insight = await national.generate_insight(ctx)
        o_insight = await opponent.generate_insight(ctx)
        t_insight = await tactical.generate_insight(ctx)
        assert all(i.persona_id for i in [n_insight, o_insight, t_insight])

    async def test_injury_and_performance_combined(self):
        injury = InjuryIntelligencePersona()
        perf = PerformanceSciencePersona()
        inj_result = await injury.assess_injury("Player A", "muscle", 7)
        load_result = await perf.analyze_player_load("Player A", 10, 25.0)
        assert "availability" in inj_result
        assert "risk_level" in load_result
