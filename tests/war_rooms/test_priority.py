"""Tests for PriorityEngine."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from sfc.war_rooms.priority.models import ConflictType, PriorityDecision
from sfc.war_rooms.priority.service import PriorityEngine
from sfc.war_rooms.registry.service import WarRoomRegistry
from sfc.war_rooms.shared.types import (
    WarRoomPriority,
    WarRoomState,
    WarRoomStatus,
    WarRoomType,
)


def make_state(
    war_room_type: WarRoomType,
    priority: WarRoomPriority,
    war_room_id: str | None = None,
    activation_time: datetime | None = None,
) -> WarRoomState:
    return WarRoomState(
        war_room_id=war_room_id or f"WR-{war_room_type.value.upper()}-TEST",
        war_room_type=war_room_type,
        status=WarRoomStatus.ACTIVE,
        priority=priority,
        activation_time=activation_time or datetime.utcnow(),
    )


@pytest.fixture
def engine() -> PriorityEngine:
    return PriorityEngine()


class TestPriorityEngineAssignment:
    def test_crisis_maps_to_p1(self, engine: PriorityEngine) -> None:
        assert engine.assign_priority(WarRoomType.CRISIS) == WarRoomPriority.P1_CRITICAL

    def test_world_cup_maps_to_p1(self, engine: PriorityEngine) -> None:
        assert engine.assign_priority(WarRoomType.WORLD_CUP) == WarRoomPriority.P1_CRITICAL

    def test_match_day_maps_to_p3(self, engine: PriorityEngine) -> None:
        assert engine.assign_priority(WarRoomType.MATCH_DAY) == WarRoomPriority.P3_MEDIUM

    def test_transfer_window_maps_to_p3(self, engine: PriorityEngine) -> None:
        assert engine.assign_priority(WarRoomType.TRANSFER_WINDOW) == WarRoomPriority.P3_MEDIUM


class TestPriorityEngineGetHighest:
    def test_returns_none_for_empty(self, engine: PriorityEngine) -> None:
        assert engine.get_highest_priority([]) is None

    def test_returns_single_item(self, engine: PriorityEngine) -> None:
        state = make_state(WarRoomType.MATCH_DAY, WarRoomPriority.P3_MEDIUM)
        result = engine.get_highest_priority([state])
        assert result is state

    def test_p1_beats_p3(self, engine: PriorityEngine) -> None:
        crisis = make_state(WarRoomType.CRISIS, WarRoomPriority.P1_CRITICAL)
        match_day = make_state(WarRoomType.MATCH_DAY, WarRoomPriority.P3_MEDIUM)
        result = engine.get_highest_priority([match_day, crisis])
        assert result is crisis

    def test_crisis_beats_world_cup_at_same_p1(self, engine: PriorityEngine) -> None:
        crisis = make_state(WarRoomType.CRISIS, WarRoomPriority.P1_CRITICAL)
        world_cup = make_state(WarRoomType.WORLD_CUP, WarRoomPriority.P1_CRITICAL)
        result = engine.get_highest_priority([world_cup, crisis])
        assert result is crisis

    def test_world_cup_beats_match_day(self, engine: PriorityEngine) -> None:
        world_cup = make_state(WarRoomType.WORLD_CUP, WarRoomPriority.P1_CRITICAL)
        match_day = make_state(WarRoomType.MATCH_DAY, WarRoomPriority.P3_MEDIUM)
        result = engine.get_highest_priority([match_day, world_cup])
        assert result is world_cup

    def test_among_equal_type_newest_wins(self, engine: PriorityEngine) -> None:
        """Among same type and priority, most recently activated wins."""
        older = make_state(
            WarRoomType.MATCH_DAY,
            WarRoomPriority.P3_MEDIUM,
            war_room_id="WR-MATCH_DAY-OLDER",
            activation_time=datetime.utcnow() - timedelta(hours=1),
        )
        newer = make_state(
            WarRoomType.MATCH_DAY,
            WarRoomPriority.P3_MEDIUM,
            war_room_id="WR-MATCH_DAY-NEWER",
            activation_time=datetime.utcnow(),
        )
        result = engine.get_highest_priority([older, newer])
        assert result is newer


class TestPriorityEngineCoexistence:
    def test_crisis_can_coexist_with_match_day(self, engine: PriorityEngine) -> None:
        assert engine.can_coexist(WarRoomType.CRISIS, WarRoomType.MATCH_DAY) is True

    def test_crisis_can_coexist_with_world_cup(self, engine: PriorityEngine) -> None:
        assert engine.can_coexist(WarRoomType.CRISIS, WarRoomType.WORLD_CUP) is True

    def test_crisis_can_coexist_with_transfer_window(self, engine: PriorityEngine) -> None:
        assert engine.can_coexist(WarRoomType.CRISIS, WarRoomType.TRANSFER_WINDOW) is True

    def test_world_cup_can_coexist_with_transfer_window(
        self, engine: PriorityEngine
    ) -> None:
        assert engine.can_coexist(WarRoomType.WORLD_CUP, WarRoomType.TRANSFER_WINDOW) is True

    def test_world_cup_can_coexist_with_match_day(self, engine: PriorityEngine) -> None:
        assert engine.can_coexist(WarRoomType.WORLD_CUP, WarRoomType.MATCH_DAY) is True

    def test_two_match_day_cannot_coexist(self, engine: PriorityEngine) -> None:
        assert engine.can_coexist(WarRoomType.MATCH_DAY, WarRoomType.MATCH_DAY) is False

    def test_two_crisis_cannot_coexist(self, engine: PriorityEngine) -> None:
        assert engine.can_coexist(WarRoomType.CRISIS, WarRoomType.CRISIS) is False

    def test_two_world_cup_cannot_coexist(self, engine: PriorityEngine) -> None:
        assert engine.can_coexist(WarRoomType.WORLD_CUP, WarRoomType.WORLD_CUP) is False

    def test_two_transfer_window_cannot_coexist(self, engine: PriorityEngine) -> None:
        assert engine.can_coexist(
            WarRoomType.TRANSFER_WINDOW, WarRoomType.TRANSFER_WINDOW
        ) is False


class TestPriorityEngineConflictResolution:
    def test_resolve_conflict_no_conflict_returns_none(
        self, engine: PriorityEngine
    ) -> None:
        crisis = make_state(WarRoomType.CRISIS, WarRoomPriority.P1_CRITICAL)
        match_day = make_state(WarRoomType.MATCH_DAY, WarRoomPriority.P3_MEDIUM)
        # These can coexist — no conflict
        result = engine.resolve_conflict([crisis, match_day])
        assert result is None

    def test_resolve_conflict_returns_priority_decision(
        self, engine: PriorityEngine
    ) -> None:
        """Two match day instances = conflict."""
        md1 = make_state(
            WarRoomType.MATCH_DAY,
            WarRoomPriority.P3_MEDIUM,
            war_room_id="WR-MD-1",
        )
        md2 = make_state(
            WarRoomType.MATCH_DAY,
            WarRoomPriority.P3_MEDIUM,
            war_room_id="WR-MD-2",
            activation_time=datetime.utcnow() + timedelta(seconds=1),
        )
        decision = engine.resolve_conflict([md1, md2])
        assert decision is not None
        assert isinstance(decision, PriorityDecision)
        assert decision.conflict_type == ConflictType.PRIORITY_CONFLICT

    def test_resolve_conflict_crisis_wins_over_match_day_in_conflict(
        self, engine: PriorityEngine
    ) -> None:
        """If both Crisis and MatchDay are passed (they can coexist) — crisis wins."""
        crisis = make_state(WarRoomType.CRISIS, WarRoomPriority.P1_CRITICAL, "WR-CRISIS-1")
        match_day = make_state(WarRoomType.MATCH_DAY, WarRoomPriority.P3_MEDIUM, "WR-MD-1")
        # They can coexist, so no conflict decision
        decision = engine.resolve_conflict([crisis, match_day])
        assert decision is None  # no conflict between coexistable types

    def test_single_war_room_no_conflict(self, engine: PriorityEngine) -> None:
        crisis = make_state(WarRoomType.CRISIS, WarRoomPriority.P1_CRITICAL)
        assert engine.resolve_conflict([crisis]) is None

    def test_empty_list_no_conflict(self, engine: PriorityEngine) -> None:
        assert engine.resolve_conflict([]) is None


class TestPriorityEngineEscalation:
    def test_escalate_sets_escalated_status(self, engine: PriorityEngine) -> None:
        registry = WarRoomRegistry()
        state = registry.activate(WarRoomType.MATCH_DAY)
        engine.escalate(state.war_room_id, registry, reason="test escalation")
        updated = registry.get_by_type(WarRoomType.MATCH_DAY)
        assert updated is not None
        assert updated.status == WarRoomStatus.ESCALATED

    def test_escalate_upgrades_priority_to_p1(self, engine: PriorityEngine) -> None:
        registry = WarRoomRegistry()
        state = registry.activate(WarRoomType.MATCH_DAY)
        assert state.priority == WarRoomPriority.P3_MEDIUM
        engine.escalate(state.war_room_id, registry, reason="test escalation")
        updated = registry.get_by_type(WarRoomType.MATCH_DAY)
        assert updated is not None
        assert updated.priority == WarRoomPriority.P1_CRITICAL

    def test_escalate_records_escalation(self, engine: PriorityEngine) -> None:
        registry = WarRoomRegistry()
        state = registry.activate(WarRoomType.MATCH_DAY)
        engine.escalate(state.war_room_id, registry, reason="important reason")
        updated = registry.get_by_type(WarRoomType.MATCH_DAY)
        assert updated is not None
        assert len(updated.escalations) == 1
        assert "important reason" in updated.escalations[0]["reason"]

    def test_escalate_nonexistent_does_not_raise(self, engine: PriorityEngine) -> None:
        registry = WarRoomRegistry()
        # Should not raise — just logs warning
        engine.escalate("WR-NONEXISTENT-0000", registry, reason="test")
