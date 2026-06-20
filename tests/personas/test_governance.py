"""Tests for PersonaGovernanceFramework."""
from __future__ import annotations

from sfc.events.bus import get_event_bus
from sfc.personas.registry.service import PersonaRegistry
from sfc.personas.governance.service import PersonaGovernanceFramework
from sfc.personas.shared.types import PersonaCategory, PersonaProfile, PersonaStatus


class TestPersonaGovernanceFramework:
    def setup_method(self):
        get_event_bus().reset()

    async def test_review_active_persona(self):
        registry = PersonaRegistry()
        governance = PersonaGovernanceFramework()
        persona = registry.get("PERSONA-GOVERNANCE-01")
        report = await governance.review(persona)
        assert report.overall_passed is True
        assert len(report.checks) == 5

    async def test_approve_valid_persona(self):
        registry = PersonaRegistry()
        governance = PersonaGovernanceFramework()
        persona = registry.get("PERSONA-STRATEGIST-01")
        approval = await governance.approve(persona)
        assert approval.approved is True
        assert approval.persona_id == "PERSONA-STRATEGIST-01"

    async def test_reject_insufficient_capabilities(self):
        governance = PersonaGovernanceFramework()
        weak_persona = PersonaProfile(
            name="Weak Persona",
            category=PersonaCategory.SPECIALIST,
            description="A persona with only one capability.",
            status=PersonaStatus.ACTIVE,
            capabilities=["single_task"],
            performance_score=70.0,
        )
        report = await governance.review(weak_persona)
        cap_check = next(
            c for c in report.checks if c.check_type.value == "capability_validation"
        )
        assert cap_check.passed is False

    async def test_assess_risk_returns_level(self):
        registry = PersonaRegistry()
        governance = PersonaGovernanceFramework()
        persona = registry.get("PERSONA-ANALYST-01")
        result = await governance.assess_risk(persona)
        assert "risk_level" in result
        assert result["risk_level"] in ("low", "medium", "high")
        assert "mitigation_steps" in result

    async def test_risk_score_low_for_high_performer(self):
        registry = PersonaRegistry()
        governance = PersonaGovernanceFramework()
        persona = registry.get("PERSONA-GOVERNANCE-01")  # performance_score=90
        report = await governance.review(persona)
        # High performer with ACTIVE status should have low risk
        assert report.risk_score == 0.0  # all checks pass

    def test_health_check(self):
        governance = PersonaGovernanceFramework()
        health = governance.health_check()
        assert health["status"] == "healthy"
        assert health["component"] == "PersonaGovernanceFramework"
