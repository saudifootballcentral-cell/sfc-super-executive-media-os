"""Tests for ResourceAllocationEngine."""

from __future__ import annotations

import pytest

from sfc.war_rooms.registry.service import WarRoomRegistry
from sfc.war_rooms.resource_allocation.models import AllocationPlan, ResourceUtilization
from sfc.war_rooms.resource_allocation.service import ResourceAllocationEngine
from sfc.war_rooms.shared.types import WarRoomType


@pytest.fixture
def registry() -> WarRoomRegistry:
    return WarRoomRegistry()


@pytest.fixture
def engine(registry: WarRoomRegistry) -> ResourceAllocationEngine:
    return ResourceAllocationEngine(registry)


class TestResourceAllocationBasic:
    def test_allocate_returns_allocation_plan(
        self, engine: ResourceAllocationEngine, registry: WarRoomRegistry
    ) -> None:
        state = registry.activate(WarRoomType.MATCH_DAY)
        plan = engine.allocate(state.war_room_id, WarRoomType.MATCH_DAY)
        assert isinstance(plan, AllocationPlan)
        assert plan.war_room_id == state.war_room_id

    def test_allocate_plan_has_resources(
        self, engine: ResourceAllocationEngine, registry: WarRoomRegistry
    ) -> None:
        state = registry.activate(WarRoomType.MATCH_DAY)
        plan = engine.allocate(state.war_room_id, WarRoomType.MATCH_DAY)
        assert plan.resources.priority_slots > 0
        assert len(plan.resources.divisions) > 0
        assert plan.resources.memory_namespace == "match_day"

    def test_allocate_crisis_gets_correct_profile(
        self, engine: ResourceAllocationEngine, registry: WarRoomRegistry
    ) -> None:
        state = registry.activate(WarRoomType.CRISIS)
        plan = engine.allocate(state.war_room_id, WarRoomType.CRISIS)
        assert plan.resources.priority_slots == 5
        assert plan.resources.cost_budget_usd == 25.0
        assert plan.resources.memory_namespace == "crisis"

    def test_allocate_world_cup_gets_correct_profile(
        self, engine: ResourceAllocationEngine, registry: WarRoomRegistry
    ) -> None:
        state = registry.activate(WarRoomType.WORLD_CUP)
        plan = engine.allocate(state.war_room_id, WarRoomType.WORLD_CUP)
        assert plan.resources.priority_slots == 8
        assert plan.resources.memory_namespace == "world_cup"

    def test_allocate_transfer_window_gets_correct_profile(
        self, engine: ResourceAllocationEngine, registry: WarRoomRegistry
    ) -> None:
        state = registry.activate(WarRoomType.TRANSFER_WINDOW)
        plan = engine.allocate(state.war_room_id, WarRoomType.TRANSFER_WINDOW)
        assert plan.resources.priority_slots == 3
        assert plan.resources.memory_namespace == "transfer_window"


class TestResourceAllocationRelease:
    def test_release_frees_slots(
        self, engine: ResourceAllocationEngine, registry: WarRoomRegistry
    ) -> None:
        state = registry.activate(WarRoomType.MATCH_DAY)
        engine.allocate(state.war_room_id, WarRoomType.MATCH_DAY)
        assert engine._slots_used == 4  # Match Day uses 4 slots
        engine.release(state.war_room_id)
        assert engine._slots_used == 0

    def test_release_nonexistent_does_not_raise(
        self, engine: ResourceAllocationEngine
    ) -> None:
        # Should not raise — just logs warning
        engine.release("WR-NONEXISTENT-0000")

    def test_get_allocation_returns_plan(
        self, engine: ResourceAllocationEngine, registry: WarRoomRegistry
    ) -> None:
        state = registry.activate(WarRoomType.MATCH_DAY)
        plan = engine.allocate(state.war_room_id, WarRoomType.MATCH_DAY)
        retrieved = engine.get_allocation(state.war_room_id)
        assert retrieved is not None
        assert retrieved.plan_id == plan.plan_id

    def test_get_allocation_returns_none_after_release(
        self, engine: ResourceAllocationEngine, registry: WarRoomRegistry
    ) -> None:
        state = registry.activate(WarRoomType.MATCH_DAY)
        engine.allocate(state.war_room_id, WarRoomType.MATCH_DAY)
        engine.release(state.war_room_id)
        assert engine.get_allocation(state.war_room_id) is None


class TestResourceUtilization:
    def test_get_utilization_empty(self, engine: ResourceAllocationEngine) -> None:
        util = engine.get_utilization()
        assert isinstance(util, ResourceUtilization)
        assert util.used_slots == 0
        assert util.total_slots == 10

    def test_get_utilization_reflects_used_slots(
        self, engine: ResourceAllocationEngine, registry: WarRoomRegistry
    ) -> None:
        state = registry.activate(WarRoomType.MATCH_DAY)
        engine.allocate(state.war_room_id, WarRoomType.MATCH_DAY)
        util = engine.get_utilization()
        assert util.used_slots == 4

    def test_get_utilization_budget_tracked(
        self, engine: ResourceAllocationEngine, registry: WarRoomRegistry
    ) -> None:
        state = registry.activate(WarRoomType.CRISIS)
        engine.allocate(state.war_room_id, WarRoomType.CRISIS)
        util = engine.get_utilization()
        assert util.budget_used_usd == 25.0
        assert util.budget_remaining_usd == 75.0

    def test_get_utilization_has_division_utilization(
        self, engine: ResourceAllocationEngine, registry: WarRoomRegistry
    ) -> None:
        state = registry.activate(WarRoomType.MATCH_DAY)
        engine.allocate(state.war_room_id, WarRoomType.MATCH_DAY)
        util = engine.get_utilization()
        assert isinstance(util.division_utilization, dict)
        assert "intelligence" in util.division_utilization


class TestCanAllocate:
    def test_can_allocate_initially_true(
        self, engine: ResourceAllocationEngine
    ) -> None:
        assert engine.can_allocate(WarRoomType.MATCH_DAY) is True
        assert engine.can_allocate(WarRoomType.CRISIS) is True

    def test_can_allocate_returns_false_when_slots_exhausted(
        self, engine: ResourceAllocationEngine, registry: WarRoomRegistry
    ) -> None:
        """World Cup uses 8 slots, leaving 2. Crisis needs 5 — should fail can_allocate."""
        state_wc = registry.activate(WarRoomType.WORLD_CUP)
        engine.allocate(state_wc.war_room_id, WarRoomType.WORLD_CUP)
        # 8 slots used, 2 remaining — Crisis needs 5
        assert engine.can_allocate(WarRoomType.CRISIS) is False

    def test_can_allocate_transfer_window_after_match_day(
        self, engine: ResourceAllocationEngine, registry: WarRoomRegistry
    ) -> None:
        """Match Day (4) + Transfer Window (3) = 7 total — within capacity."""
        state_md = registry.activate(WarRoomType.MATCH_DAY)
        engine.allocate(state_md.war_room_id, WarRoomType.MATCH_DAY)
        assert engine.can_allocate(WarRoomType.TRANSFER_WINDOW) is True


class TestCapacityReport:
    def test_capacity_report_format(
        self, engine: ResourceAllocationEngine, registry: WarRoomRegistry
    ) -> None:
        state = registry.activate(WarRoomType.MATCH_DAY)
        engine.allocate(state.war_room_id, WarRoomType.MATCH_DAY)
        report = engine.capacity_report()
        assert "total_slots" in report
        assert "used_slots" in report
        assert "available_slots" in report
        assert "slot_utilization_pct" in report
        assert "active_allocations" in report
        assert report["total_slots"] == 10
        assert report["used_slots"] == 4
        assert report["available_slots"] == 6
