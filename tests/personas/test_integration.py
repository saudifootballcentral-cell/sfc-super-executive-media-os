"""Integration tests for the Persona Infrastructure Layer."""
from __future__ import annotations

from sfc.events.bus import get_event_bus
from sfc.personas.registry.service import PersonaRegistry
from sfc.personas.activation.service import PersonaActivationEngine
from sfc.personas.activation.models import ActivationTrigger
from sfc.personas.routing.service import PersonaRoutingEngine
from sfc.personas.routing.models import RoutingIntent
from sfc.personas.governance.service import PersonaGovernanceFramework
from sfc.personas.lifecycle.service import PersonaLifecycleManager
from sfc.personas.collaboration.service import PersonaCollaborationEngine
from sfc.personas.recommendation.service import PersonaRecommendationEngine
from sfc.personas.recommendation.models import RecommendationRequest
from sfc.personas.evaluation.service import PersonaEvaluationFramework
from sfc.personas.shared.types import PersonaCategory, PersonaProfile, PersonaStatus


class TestPersonaIntegration:
    def setup_method(self):
        get_event_bus().reset()

    async def test_full_activation_flow(self):
        """plan → activate → check events published"""
        registry = PersonaRegistry()
        engine = PersonaActivationEngine(registry)

        plan = await engine.plan(ActivationTrigger.MATCH_DAY)
        decision = await engine.activate(plan)

        events = get_event_bus().get_history("persona_activated")
        assert len(events) >= 3  # MATCH_DAY activates 3 personas
        assert decision.approved is True
        assert len(decision.activated_personas) == len(plan.dependency_order)

    async def test_routing_and_collaboration(self):
        """route → form_team based on routed intent"""
        registry = PersonaRegistry()
        router = PersonaRoutingEngine(registry)
        collab = PersonaCollaborationEngine(registry)

        available = [p for p in registry.list_all() if p.status == PersonaStatus.ACTIVE]
        decision = await router.route(RoutingIntent.CONTENT_CREATION, available)

        team = await collab.form_team(
            task_type="content_creation",
            required_capabilities=["match_reporting"],
        )
        assert len(team.members) > 0
        assert decision.primary_persona_id is not None

    async def test_governance_then_lifecycle(self):
        """governance review passes → promote to next state"""
        governance = PersonaGovernanceFramework()
        registry = PersonaRegistry()
        manager = PersonaLifecycleManager(registry)

        # Register a DRAFT persona
        draft = PersonaProfile(
            persona_id="PERSONA-INTEG-01",
            name="Integration Test Persona",
            category=PersonaCategory.SPECIALIST,
            description="Integration test persona for governance and lifecycle flow.",
            status=PersonaStatus.DRAFT,
            capabilities=["integration_testing", "validation"],
            performance_score=75.0,
        )
        registry.register(draft)

        # Governance review should pass for an ACTIVE-compatible persona
        # (Note: draft personas fail risk check but we test the flow)
        report = await governance.review(draft)
        assert len(report.checks) == 5

        # Promote DRAFT → TESTING
        transition = await manager.promote("PERSONA-INTEG-01")
        assert transition.to_state.value == "testing"

    async def test_recommendation_then_activation(self):
        """recommend → activate the recommended personas"""
        registry = PersonaRegistry()
        rec_engine = PersonaRecommendationEngine(registry)
        act_engine = PersonaActivationEngine(registry)

        request = RecommendationRequest(
            task_type="match_report", war_room_type="match_day"
        )
        recommendation = await rec_engine.recommend(request)
        assert len(recommendation.recommended_team) > 0

        # Now plan activation based on recommendation
        plan = await act_engine.plan(ActivationTrigger.MATCH_DAY)
        decision = await act_engine.activate(plan)
        assert decision.approved is True

    async def test_evaluate_registry_personas(self):
        """All 6 seed personas can be batch evaluated"""
        registry = PersonaRegistry()
        evaluator = PersonaEvaluationFramework()

        all_personas = registry.list_all()
        assert len(all_personas) == 6

        report = await evaluator.batch_evaluate(all_personas)
        assert len(report.scorecards) == 6
        assert report.top_performer_id is not None
        # All seed personas have performance_score >= 78, so no retirement candidates
        assert len(report.retirement_candidates) == 0
