"""Tests for PersonaRegistry."""
from __future__ import annotations

from sfc.events.bus import get_event_bus
from sfc.personas.registry.service import PersonaRegistry
from sfc.personas.registry.models import PersonaFilter
from sfc.personas.shared.types import PersonaCategory, PersonaProfile, PersonaStatus


class TestPersonaRegistry:
    def setup_method(self):
        get_event_bus().reset()

    def test_seed_personas_registered(self):
        registry = PersonaRegistry()
        all_personas = registry.list_all()
        assert len(all_personas) == 6

    def test_register_custom_persona(self):
        registry = PersonaRegistry()
        profile = PersonaProfile(
            persona_id="PERSONA-TEST-01",
            name="Test Persona",
            category=PersonaCategory.SPECIALIST,
            description="A test persona for unit testing.",
            status=PersonaStatus.DRAFT,
        )
        registered = registry.register(profile)
        assert registered.persona_id == "PERSONA-TEST-01"
        retrieved = registry.get("PERSONA-TEST-01")
        assert retrieved is not None
        assert retrieved.name == "Test Persona"

    def test_list_filter_by_status(self):
        registry = PersonaRegistry()
        # Add a draft persona
        profile = PersonaProfile(
            name="Draft Persona",
            category=PersonaCategory.SPECIALIST,
            description="Draft only.",
            status=PersonaStatus.DRAFT,
        )
        registry.register(profile)
        active_only = registry.list_all(filter=PersonaFilter(status=PersonaStatus.ACTIVE))
        assert all(p.status == PersonaStatus.ACTIVE for p in active_only)
        assert len(active_only) == 6  # only the 6 seed personas are ACTIVE

    def test_track_activation(self):
        registry = PersonaRegistry()
        initial = registry.get("PERSONA-JOURNALIST-01")
        assert initial is not None
        initial_count = initial.activation_count
        registry.track_activation("PERSONA-JOURNALIST-01", trigger="match_day")
        updated = registry.get("PERSONA-JOURNALIST-01")
        assert updated.activation_count == initial_count + 1

    def test_retire_persona(self):
        registry = PersonaRegistry()
        retired = registry.retire("PERSONA-ANALYST-01")
        assert retired.status == PersonaStatus.RETIRED
        retrieved = registry.get("PERSONA-ANALYST-01")
        assert retrieved.status == PersonaStatus.RETIRED

    def test_registry_report(self):
        registry = PersonaRegistry()
        report = registry.report()
        assert report.total_personas == 6
        assert report.avg_performance_score > 0
        assert "active" in report.by_status
        assert report.by_status["active"] == 6
