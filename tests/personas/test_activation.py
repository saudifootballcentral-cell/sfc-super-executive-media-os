"""Tests for PersonaActivationEngine."""
from __future__ import annotations

from sfc.events.bus import get_event_bus
from sfc.personas.registry.service import PersonaRegistry
from sfc.personas.activation.service import PersonaActivationEngine
from sfc.personas.activation.models import ActivationTrigger


class TestPersonaActivationEngine:
    def setup_method(self):
        get_event_bus().reset()

    async def test_plan_match_day(self):
        registry = PersonaRegistry()
        engine = PersonaActivationEngine(registry)
        plan = await engine.plan(ActivationTrigger.MATCH_DAY)
        assert "PERSONA-JOURNALIST-01" in plan.selected_personas
        assert "PERSONA-ANALYST-01" in plan.selected_personas

    async def test_plan_breaking_news(self):
        registry = PersonaRegistry()
        engine = PersonaActivationEngine(registry)
        plan = await engine.plan(ActivationTrigger.BREAKING_NEWS)
        assert "PERSONA-JOURNALIST-01" in plan.selected_personas
        assert "PERSONA-GOVERNANCE-01" in plan.selected_personas

    async def test_activate_publishes_events(self):
        registry = PersonaRegistry()
        engine = PersonaActivationEngine(registry)
        plan = await engine.plan(ActivationTrigger.CONTENT_REQUEST)
        decision = await engine.activate(plan)
        history = get_event_bus().get_history("persona_activated")
        assert len(history) > 0
        assert decision.approved is True

    async def test_deactivate_publishes_event(self):
        registry = PersonaRegistry()
        engine = PersonaActivationEngine(registry)
        await engine.deactivate("PERSONA-JOURNALIST-01", run_id="test-run")
        history = get_event_bus().get_history("persona_deactivated")
        assert len(history) == 1
        assert history[0].payload["persona_id"] == "PERSONA-JOURNALIST-01"

    async def test_cost_estimate(self):
        registry = PersonaRegistry()
        engine = PersonaActivationEngine(registry)
        plan = await engine.plan(ActivationTrigger.WORLD_CUP)
        assert plan.estimated_cost_usd > 0

    def test_health_check(self):
        registry = PersonaRegistry()
        engine = PersonaActivationEngine(registry)
        health = engine.health_check()
        assert health["status"] == "healthy"
        assert health["component"] == "PersonaActivationEngine"
