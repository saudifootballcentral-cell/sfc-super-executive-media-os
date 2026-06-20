"""Tests for PersonaPerformanceAnalytics."""
from __future__ import annotations

from sfc.events.bus import get_event_bus
from sfc.personas.registry.service import PersonaRegistry
from sfc.personas.analytics.service import PersonaPerformanceAnalytics
from sfc.personas.analytics.models import AnalyticsPeriod


class TestPersonaPerformanceAnalytics:
    def setup_method(self):
        get_event_bus().reset()

    async def test_build_dashboard(self):
        registry = PersonaRegistry()
        analytics = PersonaPerformanceAnalytics(registry)
        dashboard = await analytics.build_dashboard()
        assert dashboard.total_personas == 6
        assert dashboard.active_personas == 6
        assert len(dashboard.rankings) > 0
        assert dashboard.top_performer is not None

    async def test_rank_personas(self):
        registry = PersonaRegistry()
        analytics = PersonaPerformanceAnalytics(registry)
        rankings = await analytics.rank_personas()
        assert rankings[0].rank == 1
        # Governance has highest score (90.0)
        assert rankings[0].persona_id == "PERSONA-GOVERNANCE-01"
        assert rankings[0].overall_score >= rankings[1].overall_score

    async def test_optimization_recommendations_low_score(self):
        registry = PersonaRegistry()
        analytics = PersonaPerformanceAnalytics(registry)
        # Revenue persona has score 78 → medium bracket
        rec = await analytics.get_optimization_recommendations("PERSONA-REVENUE-01")
        assert "Improve collaboration score" in rec.actions
        assert rec.priority == "medium"

    async def test_generate_report_returns_dict(self):
        registry = PersonaRegistry()
        analytics = PersonaPerformanceAnalytics(registry)
        report = await analytics.generate_report(period=AnalyticsPeriod.SESSION)
        assert isinstance(report, dict)
        assert "period" in report
        assert report["period"] == "session"
        assert "rankings_count" in report

    def test_health_check(self):
        registry = PersonaRegistry()
        analytics = PersonaPerformanceAnalytics(registry)
        health = analytics.health_check()
        assert health["status"] == "healthy"
        assert health["component"] == "PersonaPerformanceAnalytics"
