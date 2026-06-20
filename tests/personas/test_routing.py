"""Tests for PersonaRoutingEngine."""
from __future__ import annotations

from sfc.events.bus import get_event_bus
from sfc.personas.registry.service import PersonaRegistry
from sfc.personas.routing.service import PersonaRoutingEngine
from sfc.personas.routing.models import RoutingIntent
from sfc.personas.shared.types import PersonaStatus


class TestPersonaRoutingEngine:
    def setup_method(self):
        get_event_bus().reset()

    async def test_classify_match_intent(self):
        registry = PersonaRegistry()
        engine = PersonaRoutingEngine(registry)
        intent = await engine.classify_intent("match_report")
        assert intent == RoutingIntent.CONTENT_CREATION

    async def test_classify_analytics_intent(self):
        registry = PersonaRegistry()
        engine = PersonaRoutingEngine(registry)
        intent = await engine.classify_intent("analytics_dashboard")
        assert intent == RoutingIntent.DATA_ANALYSIS

    async def test_route_selects_primary(self):
        registry = PersonaRegistry()
        engine = PersonaRoutingEngine(registry)
        available = [p for p in registry.list_all() if p.status == PersonaStatus.ACTIVE]
        decision = await engine.route(RoutingIntent.CONTENT_CREATION, available)
        assert decision.primary_persona_id == "PERSONA-JOURNALIST-01"
        assert decision.confidence > 0

    async def test_build_execution_plan(self):
        registry = PersonaRegistry()
        engine = PersonaRoutingEngine(registry)
        available = [p for p in registry.list_all() if p.status == PersonaStatus.ACTIVE]
        decision = await engine.route(RoutingIntent.DATA_ANALYSIS, available)
        plan = await engine.build_execution_plan(decision)
        assert len(plan.steps) >= 1
        assert plan.steps[0]["persona_id"] == decision.primary_persona_id

    async def test_workload_distribution(self):
        registry = PersonaRegistry()
        engine = PersonaRoutingEngine(registry)
        persona_ids = ["PERSONA-JOURNALIST-01", "PERSONA-ANALYST-01", "PERSONA-CREATIVE-01"]
        distribution = await engine.distribute_workload(persona_ids, task_count=6)
        assert sum(distribution.values()) == 6
        # Each should get exactly 2 tasks
        assert all(v == 2 for v in distribution.values())
