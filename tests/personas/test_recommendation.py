"""Tests for PersonaRecommendationEngine."""
from __future__ import annotations

from sfc.events.bus import get_event_bus
from sfc.personas.registry.service import PersonaRegistry
from sfc.personas.recommendation.service import PersonaRecommendationEngine
from sfc.personas.recommendation.models import RecommendationRequest


class TestPersonaRecommendationEngine:
    def setup_method(self):
        get_event_bus().reset()

    async def test_recommend_for_match_day(self):
        registry = PersonaRegistry()
        engine = PersonaRecommendationEngine(registry)
        request = RecommendationRequest(
            task_type="match_report", war_room_type="match_day"
        )
        rec = await engine.recommend(request)
        # Journalism persona should be in recommended team
        assert "PERSONA-JOURNALIST-01" in rec.recommended_team

    async def test_recommend_for_transfer_window(self):
        registry = PersonaRegistry()
        engine = PersonaRecommendationEngine(registry)
        request = RecommendationRequest(
            task_type="transfer_news", war_room_type="transfer"
        )
        rec = await engine.recommend(request)
        # Revenue or Journalism persona should be included
        assert any(
            pid in rec.recommended_team
            for pid in ["PERSONA-REVENUE-01", "PERSONA-JOURNALIST-01"]
        )

    async def test_confidence_score_range(self):
        registry = PersonaRegistry()
        engine = PersonaRecommendationEngine(registry)
        request = RecommendationRequest(task_type="content_creation")
        rec = await engine.recommend(request)
        assert 0.0 <= rec.confidence_score <= 1.0

    async def test_recommend_team_returns_ids(self):
        registry = PersonaRegistry()
        engine = PersonaRecommendationEngine(registry)
        team = await engine.recommend_team("match_report", team_size=3)
        assert isinstance(team, list)
        assert len(team) <= 3
        assert all(isinstance(pid, str) for pid in team)

    def test_health_check(self):
        registry = PersonaRegistry()
        engine = PersonaRecommendationEngine(registry)
        health = engine.health_check()
        assert health["status"] == "healthy"
        assert health["component"] == "PersonaRecommendationEngine"
