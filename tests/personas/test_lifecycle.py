"""Tests for PersonaLifecycleManager."""
from __future__ import annotations

from sfc.events.bus import get_event_bus
from sfc.personas.registry.service import PersonaRegistry
from sfc.personas.lifecycle.service import PersonaLifecycleManager
from sfc.personas.shared.types import PersonaCategory, PersonaProfile, PersonaStatus


class TestPersonaLifecycleManager:
    def setup_method(self):
        get_event_bus().reset()

    async def test_promote_draft_to_testing(self):
        registry = PersonaRegistry()
        # Register a DRAFT persona first
        draft = PersonaProfile(
            persona_id="PERSONA-DRAFT-TEST",
            name="Draft Test",
            category=PersonaCategory.SPECIALIST,
            description="Draft lifecycle test persona.",
            status=PersonaStatus.DRAFT,
        )
        registry.register(draft)
        manager = PersonaLifecycleManager(registry)
        transition = await manager.promote("PERSONA-DRAFT-TEST", reason="ready for testing")
        assert transition.to_state.value == "testing"
        updated = registry.get("PERSONA-DRAFT-TEST")
        assert updated.status == PersonaStatus.TESTING

    async def test_promote_testing_to_active(self):
        registry = PersonaRegistry()
        draft = PersonaProfile(
            persona_id="PERSONA-TESTING-01",
            name="Testing Persona",
            category=PersonaCategory.SPECIALIST,
            description="Testing lifecycle persona.",
            status=PersonaStatus.TESTING,
        )
        registry.register(draft)
        manager = PersonaLifecycleManager(registry)
        transition = await manager.promote("PERSONA-TESTING-01")
        assert transition.to_state.value == "active"

    async def test_retire_persona(self):
        registry = PersonaRegistry()
        manager = PersonaLifecycleManager(registry)
        transition = await manager.retire("PERSONA-CREATIVE-01", reason="low performance")
        assert transition.to_state.value == "retired"
        updated = registry.get("PERSONA-CREATIVE-01")
        assert updated.status == PersonaStatus.RETIRED

    async def test_create_version(self):
        registry = PersonaRegistry()
        manager = PersonaLifecycleManager(registry)
        record = await manager.create_version(
            "PERSONA-JOURNALIST-01",
            changes=["Added Arabic language support", "Improved headline generation"],
        )
        assert record.version == "1.1.0"
        updated = registry.get("PERSONA-JOURNALIST-01")
        assert updated.version == "1.1.0"

    async def test_plan_migration(self):
        registry = PersonaRegistry()
        manager = PersonaLifecycleManager(registry)
        plan = await manager.plan_migration("PERSONA-JOURNALIST-01", "PERSONA-JOURNALIST-02")
        assert len(plan.steps) > 0
        assert plan.from_persona_id == "PERSONA-JOURNALIST-01"
        assert plan.to_persona_id == "PERSONA-JOURNALIST-02"

    async def test_lifecycle_report(self):
        registry = PersonaRegistry()
        manager = PersonaLifecycleManager(registry)
        report = await manager.report(period="session")
        assert report.active_count == 6
        assert report.period == "session"
        assert isinstance(report.transitions, list)
