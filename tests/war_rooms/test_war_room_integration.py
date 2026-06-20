"""Integration tests for War Rooms subsystem."""

from __future__ import annotations

import pytest

from sfc.events.bus import get_event_bus
from sfc.war_rooms.activation.models import ActivationRequest, ActivationTrigger
from sfc.war_rooms.activation.service import ActivationEngine
from sfc.war_rooms.crisis.models import CrisisEvent, CrisisSeverity, CrisisType
from sfc.war_rooms.crisis.service import CrisisWarRoom
from sfc.war_rooms.deactivation.service import DeactivationEngine
from sfc.war_rooms.match_day.models import MatchInfo
from sfc.war_rooms.match_day.service import MatchDayWarRoom
from sfc.war_rooms.priority.service import PriorityEngine
from sfc.war_rooms.registry.service import WarRoomRegistry
from sfc.war_rooms.resource_allocation.service import ResourceAllocationEngine
from sfc.war_rooms.shared.types import WarRoomPriority, WarRoomStatus, WarRoomType


@pytest.fixture(autouse=True)
def reset_event_bus() -> None:
    """Reset event bus between tests to avoid cross-contamination."""
    bus = get_event_bus()
    bus.reset()
    yield
    bus.reset()


@pytest.fixture
def registry() -> WarRoomRegistry:
    return WarRoomRegistry()


class TestPriorityConflictResolution:
    def test_crisis_beats_match_day_in_priority_resolution(
        self, registry: WarRoomRegistry
    ) -> None:
        """PriorityEngine correctly identifies Crisis > MatchDay."""
        engine = PriorityEngine()
        crisis_state = registry.activate(WarRoomType.CRISIS)
        match_day_state = registry.activate(WarRoomType.MATCH_DAY)

        highest = engine.get_highest_priority([match_day_state, crisis_state])
        assert highest is not None
        assert highest.war_room_type == WarRoomType.CRISIS
        assert highest.priority == WarRoomPriority.P1_CRITICAL

    def test_world_cup_beats_transfer_window(
        self, registry: WarRoomRegistry
    ) -> None:
        engine = PriorityEngine()
        wc_state = registry.activate(WarRoomType.WORLD_CUP)
        tw_state = registry.activate(WarRoomType.TRANSFER_WINDOW)

        highest = engine.get_highest_priority([tw_state, wc_state])
        assert highest is not None
        assert highest.war_room_type == WarRoomType.WORLD_CUP


class TestCrisisActivationPublishesEvent:
    @pytest.mark.asyncio
    async def test_crisis_activation_publishes_war_room_activated(
        self, registry: WarRoomRegistry
    ) -> None:
        """Crisis activation publishes WarRoomActivated event."""
        bus = get_event_bus()
        published_events: list = []

        def capture(event):
            published_events.append(event)

        bus.subscribe("war_room_activated", capture)

        engine = ActivationEngine(registry)
        request = ActivationRequest(
            war_room_type=WarRoomType.CRISIS,
            trigger=ActivationTrigger.CRISIS_DETECTED,
        )
        result = await engine.activate(request)
        assert result.success is True
        assert len(published_events) >= 1
        event = published_events[0]
        assert event.event_type == "war_room_activated"

    @pytest.mark.asyncio
    async def test_crisis_event_type_publishes_crisis_triggered(
        self, registry: WarRoomRegistry
    ) -> None:
        """activate_by_event('crisis_detected') publishes CrisisTriggered event."""
        bus = get_event_bus()
        published_events: list = []

        def capture(event):
            published_events.append(event)

        bus.subscribe("crisis_triggered", capture)

        engine = ActivationEngine(registry)
        await engine.activate_by_event("crisis_detected", metadata={"description": "Test"})
        assert len(published_events) >= 1
        assert published_events[0].event_type == "crisis_triggered"


class TestActivationEngineMapsEvents:
    @pytest.mark.asyncio
    async def test_crisis_detected_activates_crisis_war_room(
        self, registry: WarRoomRegistry
    ) -> None:
        engine = ActivationEngine(registry)
        result = await engine.activate_by_event("crisis_detected")
        assert result is not None
        assert result.success is True
        assert result.war_room_state is not None
        assert result.war_room_state.war_room_type == WarRoomType.CRISIS

    @pytest.mark.asyncio
    async def test_match_triggered_activates_match_day_war_room(
        self, registry: WarRoomRegistry
    ) -> None:
        engine = ActivationEngine(registry)
        result = await engine.activate_by_event("match_triggered")
        assert result is not None
        assert result.war_room_state is not None
        assert result.war_room_state.war_room_type == WarRoomType.MATCH_DAY

    @pytest.mark.asyncio
    async def test_world_cup_triggered_activates_world_cup_war_room(
        self, registry: WarRoomRegistry
    ) -> None:
        engine = ActivationEngine(registry)
        result = await engine.activate_by_event("world_cup_triggered")
        assert result is not None
        assert result.war_room_state is not None
        assert result.war_room_state.war_room_type == WarRoomType.WORLD_CUP

    @pytest.mark.asyncio
    async def test_transfer_window_triggered_activates_transfer_window(
        self, registry: WarRoomRegistry
    ) -> None:
        engine = ActivationEngine(registry)
        result = await engine.activate_by_event("transfer_window_triggered")
        assert result is not None
        assert result.war_room_state is not None
        assert result.war_room_state.war_room_type == WarRoomType.TRANSFER_WINDOW


class TestRegistryAndResourceAllocationIntegration:
    def test_activate_war_room_allocates_resources(
        self, registry: WarRoomRegistry
    ) -> None:
        alloc_engine = ResourceAllocationEngine(registry)
        state = registry.activate(WarRoomType.MATCH_DAY)
        plan = alloc_engine.allocate(state.war_room_id, WarRoomType.MATCH_DAY)

        assert plan is not None
        assert alloc_engine._slots_used == 4  # Match Day uses 4 slots
        util = alloc_engine.get_utilization()
        assert util.used_slots == 4

    def test_deactivate_releases_resources(
        self, registry: WarRoomRegistry
    ) -> None:
        alloc_engine = ResourceAllocationEngine(registry)
        state = registry.activate(WarRoomType.MATCH_DAY)
        alloc_engine.allocate(state.war_room_id, WarRoomType.MATCH_DAY)

        assert alloc_engine._slots_used == 4
        alloc_engine.release(state.war_room_id)
        assert alloc_engine._slots_used == 0

    def test_full_lifecycle_activate_deactivate(
        self, registry: WarRoomRegistry
    ) -> None:
        alloc_engine = ResourceAllocationEngine(registry)
        state = registry.activate(WarRoomType.CRISIS)
        alloc_engine.allocate(state.war_room_id, WarRoomType.CRISIS)

        assert alloc_engine._slots_used == 5
        alloc_engine.release(state.war_room_id)
        registry.deactivate(state.war_room_id)

        assert alloc_engine._slots_used == 0
        assert len(registry.get_active()) == 0
        assert len(registry.get_history()) == 1


class TestDuplicateActivationBlocked:
    @pytest.mark.asyncio
    async def test_two_match_day_activations_second_blocked(
        self, registry: WarRoomRegistry
    ) -> None:
        engine = ActivationEngine(registry)
        request = ActivationRequest(
            war_room_type=WarRoomType.MATCH_DAY,
            trigger=ActivationTrigger.MATCH_SCHEDULED,
        )
        result1 = await engine.activate(request)
        result2 = await engine.activate(request)

        assert result1.success is True
        assert result2.success is False
        assert len(registry.get_active()) == 1

    @pytest.mark.asyncio
    async def test_two_crisis_activations_second_blocked(
        self, registry: WarRoomRegistry
    ) -> None:
        engine = ActivationEngine(registry)
        request = ActivationRequest(
            war_room_type=WarRoomType.CRISIS,
            trigger=ActivationTrigger.CRISIS_DETECTED,
        )
        result1 = await engine.activate(request)
        result2 = await engine.activate(request)

        assert result1.success is True
        assert result2.success is False


class TestDeactivationEngineIntegration:
    @pytest.mark.asyncio
    async def test_deactivation_generates_closure_report(
        self, registry: WarRoomRegistry
    ) -> None:
        state = registry.activate(WarRoomType.MATCH_DAY)
        engine = DeactivationEngine(registry)
        report = await engine.deactivate(state.war_room_id, reason="test_complete")

        assert report is not None
        assert report.war_room_id == state.war_room_id
        assert report.final_status == "closed"
        assert report.war_room_type == str(WarRoomType.MATCH_DAY)

    @pytest.mark.asyncio
    async def test_deactivation_publishes_war_room_closed_event(
        self, registry: WarRoomRegistry
    ) -> None:
        bus = get_event_bus()
        published_events: list = []

        def capture(event):
            published_events.append(event)

        bus.subscribe("war_room_closed", capture)

        state = registry.activate(WarRoomType.CRISIS)
        engine = DeactivationEngine(registry)
        await engine.deactivate(state.war_room_id)

        assert len(published_events) >= 1
        assert published_events[0].event_type == "war_room_closed"


class TestCrisisWarRoomFullFlow:
    @pytest.mark.asyncio
    async def test_crisis_full_lifecycle(
        self, registry: WarRoomRegistry
    ) -> None:
        """Full crisis flow: activate → assess → resolve → deactivate."""
        war_room = CrisisWarRoom(registry)
        crisis_event = CrisisEvent(
            crisis_type=CrisisType.REPUTATION_RISK,
            severity=CrisisSeverity.CRITICAL,
            description="Major reputation incident.",
        )

        # Activate
        state = await war_room.activate(crisis_event)
        assert state.priority == WarRoomPriority.P1_CRITICAL

        # Assess
        report = await war_room.assess_crisis(crisis_event)
        assert report.status == "open"
        assert len(report.containment_actions) > 0

        # Resolve
        resolved = await war_room.resolve_crisis(crisis_event.crisis_id, "Incident contained")
        assert resolved.status == "resolved"

        # Deactivate
        closure = await war_room.deactivate()
        assert closure.final_status == "closed"


class TestMatchDayWarRoomFullFlow:
    @pytest.mark.asyncio
    async def test_match_day_full_lifecycle(
        self, registry: WarRoomRegistry
    ) -> None:
        """Full match day flow: activate → brief → content plan → ratings → summary → deactivate."""
        from sfc.war_rooms.match_day.models import MatchPhase
        war_room = MatchDayWarRoom(registry)
        match_info = MatchInfo(home_team="Al Hilal", away_team="Al Nassr")

        # Activate
        state = await war_room.activate(match_info)
        assert state.status == WarRoomStatus.ACTIVE

        # Create brief
        brief = await war_room.create_match_brief(match_info)
        assert "home_team" in brief

        # Content plan for each phase
        for phase in [MatchPhase.PRE_MATCH, MatchPhase.LIVE, MatchPhase.POST_MATCH]:
            plan = await war_room.create_content_plan(match_info, phase)
            assert isinstance(plan, list)

        # Player ratings
        ratings = await war_room.create_player_ratings(match_info, {})
        assert len(ratings) > 0

        # Executive summary
        summary = await war_room.create_executive_summary()
        assert len(summary) > 0

        # Deactivate
        closure = await war_room.deactivate()
        assert closure.final_status == "closed"
