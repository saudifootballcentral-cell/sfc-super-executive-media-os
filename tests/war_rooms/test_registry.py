"""Tests for WarRoomRegistry."""

from __future__ import annotations

import pytest

from sfc.war_rooms.registry.models import WarRoomDefinition
from sfc.war_rooms.registry.service import WarRoomRegistry
from sfc.war_rooms.shared.types import (
    WarRoomPriority,
    WarRoomStatus,
    WarRoomType,
)


@pytest.fixture
def registry() -> WarRoomRegistry:
    return WarRoomRegistry()


class TestWarRoomRegistryDefaults:
    def test_register_defaults_on_init(self, registry: WarRoomRegistry) -> None:
        """All 4 default war room definitions registered on init."""
        assert registry.get_definition(WarRoomType.MATCH_DAY) is not None
        assert registry.get_definition(WarRoomType.WORLD_CUP) is not None
        assert registry.get_definition(WarRoomType.TRANSFER_WINDOW) is not None
        assert registry.get_definition(WarRoomType.CRISIS) is not None

    def test_default_match_day_priority(self, registry: WarRoomRegistry) -> None:
        defn = registry.get_definition(WarRoomType.MATCH_DAY)
        assert defn is not None
        assert defn.default_priority == WarRoomPriority.P3_MEDIUM

    def test_default_world_cup_priority(self, registry: WarRoomRegistry) -> None:
        defn = registry.get_definition(WarRoomType.WORLD_CUP)
        assert defn is not None
        assert defn.default_priority == WarRoomPriority.P1_CRITICAL

    def test_default_crisis_priority(self, registry: WarRoomRegistry) -> None:
        defn = registry.get_definition(WarRoomType.CRISIS)
        assert defn is not None
        assert defn.default_priority == WarRoomPriority.P1_CRITICAL

    def test_definitions_have_divisions(self, registry: WarRoomRegistry) -> None:
        for wrt in WarRoomType:
            defn = registry.get_definition(wrt)
            assert defn is not None
            assert len(defn.default_divisions) > 0


class TestWarRoomRegistryActivation:
    def test_activate_returns_war_room_state(self, registry: WarRoomRegistry) -> None:
        state = registry.activate(WarRoomType.MATCH_DAY)
        assert state is not None
        assert state.war_room_type == WarRoomType.MATCH_DAY
        assert state.status == WarRoomStatus.ACTIVE

    def test_activate_assigns_correct_priority(self, registry: WarRoomRegistry) -> None:
        state = registry.activate(WarRoomType.CRISIS)
        assert state.priority == WarRoomPriority.P1_CRITICAL

    def test_activate_assigns_war_room_id(self, registry: WarRoomRegistry) -> None:
        state = registry.activate(WarRoomType.MATCH_DAY)
        assert state.war_room_id.startswith("WR-MATCH_DAY-")

    def test_cannot_activate_same_type_twice(self, registry: WarRoomRegistry) -> None:
        registry.activate(WarRoomType.MATCH_DAY)
        with pytest.raises(ValueError, match="already active"):
            registry.activate(WarRoomType.MATCH_DAY)

    def test_can_activate_different_types(self, registry: WarRoomRegistry) -> None:
        state1 = registry.activate(WarRoomType.MATCH_DAY)
        state2 = registry.activate(WarRoomType.CRISIS)
        assert state1.war_room_id != state2.war_room_id
        assert len(registry.get_active()) == 2

    def test_activate_with_metadata(self, registry: WarRoomRegistry) -> None:
        state = registry.activate(WarRoomType.MATCH_DAY, metadata={"match_id": "test-123"})
        assert state.metadata.get("match_id") == "test-123"

    def test_activate_records_activation_time(self, registry: WarRoomRegistry) -> None:
        state = registry.activate(WarRoomType.MATCH_DAY)
        assert state.activation_time is not None

    def test_activate_assigns_divisions(self, registry: WarRoomRegistry) -> None:
        state = registry.activate(WarRoomType.MATCH_DAY)
        assert len(state.assigned_divisions) > 0


class TestWarRoomRegistryDeactivation:
    def test_deactivate_moves_to_history(self, registry: WarRoomRegistry) -> None:
        state = registry.activate(WarRoomType.MATCH_DAY)
        registry.deactivate(state.war_room_id)
        assert len(registry.get_active()) == 0
        history = registry.get_history()
        assert len(history) == 1
        assert history[0].war_room_id == state.war_room_id

    def test_deactivate_sets_closed_status(self, registry: WarRoomRegistry) -> None:
        state = registry.activate(WarRoomType.MATCH_DAY)
        closed = registry.deactivate(state.war_room_id)
        assert closed.status == WarRoomStatus.CLOSED

    def test_deactivate_records_deactivation_time(self, registry: WarRoomRegistry) -> None:
        state = registry.activate(WarRoomType.MATCH_DAY)
        closed = registry.deactivate(state.war_room_id)
        assert closed.deactivation_time is not None

    def test_deactivate_nonexistent_raises(self, registry: WarRoomRegistry) -> None:
        with pytest.raises(ValueError):
            registry.deactivate("WR-NONEXISTENT-0000")

    def test_can_reactivate_after_deactivation(self, registry: WarRoomRegistry) -> None:
        state = registry.activate(WarRoomType.MATCH_DAY)
        registry.deactivate(state.war_room_id)
        state2 = registry.activate(WarRoomType.MATCH_DAY)
        assert state2.war_room_id != state.war_room_id


class TestWarRoomRegistryQueries:
    def test_get_active_empty_initially(self, registry: WarRoomRegistry) -> None:
        assert registry.get_active() == []

    def test_get_active_returns_active_only(self, registry: WarRoomRegistry) -> None:
        state = registry.activate(WarRoomType.MATCH_DAY)
        active = registry.get_active()
        assert len(active) == 1
        assert active[0].war_room_id == state.war_room_id

    def test_get_by_type_returns_correct(self, registry: WarRoomRegistry) -> None:
        state = registry.activate(WarRoomType.CRISIS)
        found = registry.get_by_type(WarRoomType.CRISIS)
        assert found is not None
        assert found.war_room_id == state.war_room_id

    def test_get_by_type_returns_none_when_not_active(self, registry: WarRoomRegistry) -> None:
        assert registry.get_by_type(WarRoomType.CRISIS) is None

    def test_get_active_filters_correctly_after_deactivation(self, registry: WarRoomRegistry) -> None:
        state1 = registry.activate(WarRoomType.MATCH_DAY)
        registry.activate(WarRoomType.CRISIS)
        registry.deactivate(state1.war_room_id)
        active = registry.get_active()
        assert len(active) == 1
        assert active[0].war_room_type == WarRoomType.CRISIS


class TestWarRoomRegistryUpdateAndReporting:
    def test_update_state_modifies_fields(self, registry: WarRoomRegistry) -> None:
        state = registry.activate(WarRoomType.MATCH_DAY)
        registry.update_state(state.war_room_id, health_score=75.0)
        updated = registry.get_by_type(WarRoomType.MATCH_DAY)
        assert updated is not None
        assert updated.health_score == 75.0

    def test_status_report_format(self, registry: WarRoomRegistry) -> None:
        registry.activate(WarRoomType.MATCH_DAY)
        registry.activate(WarRoomType.CRISIS)
        report = registry.status_report()
        assert "active_count" in report
        assert report["active_count"] == 2
        assert "by_priority" in report
        assert "by_type" in report
        assert "total_historical" in report

    def test_health_check_always_returns(self, registry: WarRoomRegistry) -> None:
        health = registry.health_check()
        assert "status" in health
        assert health["status"] == "healthy"

    def test_register_custom_definition(self, registry: WarRoomRegistry) -> None:
        custom = WarRoomDefinition(
            war_room_id="custom-def",
            name="Custom War Room",
            war_room_type=WarRoomType.MATCH_DAY,
            default_priority=WarRoomPriority.P2_HIGH,
            default_divisions=["intelligence"],
            activation_triggers=["custom_trigger"],
        )
        registry.register(custom)
        defn = registry.get_definition(WarRoomType.MATCH_DAY)
        assert defn is not None
        assert defn.default_priority == WarRoomPriority.P2_HIGH
