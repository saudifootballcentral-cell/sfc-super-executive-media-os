"""Tests for PersonaCollaborationEngine."""
from __future__ import annotations

from sfc.events.bus import get_event_bus
from sfc.personas.registry.service import PersonaRegistry
from sfc.personas.collaboration.service import PersonaCollaborationEngine
from sfc.personas.collaboration.models import CollaborationRole


class TestPersonaCollaborationEngine:
    def setup_method(self):
        get_event_bus().reset()

    async def test_form_team_selects_members(self):
        registry = PersonaRegistry()
        engine = PersonaCollaborationEngine(registry)
        team = await engine.form_team(
            task_type="match_report", required_capabilities=["match_reporting"]
        )
        assert len(team.members) > 0
        assert team.task_type == "match_report"

    async def test_lead_role_assigned(self):
        registry = PersonaRegistry()
        engine = PersonaCollaborationEngine(registry)
        team = await engine.form_team(
            task_type="analytics", required_capabilities=["stats_analysis"]
        )
        roles = [m["role"] for m in team.members]
        assert CollaborationRole.LEAD in roles

    async def test_create_plan_has_steps(self):
        registry = PersonaRegistry()
        engine = PersonaCollaborationEngine(registry)
        team = await engine.form_team(
            task_type="campaign", required_capabilities=["campaign_creation"]
        )
        plan = await engine.create_plan(team)
        assert len(plan.workflow_steps) == len(team.members)
        assert plan.workflow_steps[0]["step"] == 1

    async def test_build_consensus(self):
        registry = PersonaRegistry()
        engine = PersonaCollaborationEngine(registry)
        team = await engine.form_team(
            task_type="strategy", required_capabilities=["strategic_planning"]
        )
        plan = await engine.create_plan(team)
        consensus = await engine.build_consensus(plan)
        assert consensus.confidence > 0
        assert len(consensus.contributions) > 0

    async def test_resolve_conflict(self):
        registry = PersonaRegistry()
        engine = PersonaCollaborationEngine(registry)
        result = await engine.resolve_conflict(
            "PERSONA-GOVERNANCE-01",  # performance_score=90
            "PERSONA-REVENUE-01",     # performance_score=78
            topic="content priority",
        )
        assert result["winner_id"] == "PERSONA-GOVERNANCE-01"
        assert "rationale" in result

    def test_health_check(self):
        registry = PersonaRegistry()
        engine = PersonaCollaborationEngine(registry)
        health = engine.health_check()
        assert health["status"] == "healthy"
        assert health["component"] == "PersonaCollaborationEngine"
