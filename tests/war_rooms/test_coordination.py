"""Tests for CrossWarRoomCoordinator."""
from __future__ import annotations

from datetime import datetime

import pytest

from sfc.events.bus import get_event_bus
from sfc.war_rooms.operations.coordination.models import (
    CoordinationMode,
    CoordinationPlan,
    ConflictResolutionReport,
)
from sfc.war_rooms.operations.coordination.service import CrossWarRoomCoordinator
from sfc.war_rooms.shared.types import (
    WarRoomPriority,
    WarRoomState,
    WarRoomStatus,
    WarRoomType,
)


def _state(war_room_type: WarRoomType, war_room_id: str | None = None) -> WarRoomState:
    return WarRoomState(
        war_room_id=war_room_id or f"WR-{war_room_type.value.upper()}-TEST",
        war_room_type=war_room_type,
        status=WarRoomStatus.ACTIVE,
        priority=WarRoomPriority.P1_CRITICAL,
        assigned_divisions=["intelligence", "editorial", "publishing"],
        activation_time=datetime.utcnow(),
    )


class TestCrossWarRoomCoordinator:
    def setup_method(self) -> None:
        get_event_bus().reset()
        self.service = CrossWarRoomCoordinator()

    async def test_coordinate_empty_returns_plan(self) -> None:
        plan = await self.service.coordinate([])
        assert isinstance(plan, CoordinationPlan)
        assert plan.mode == CoordinationMode.PARALLEL

    async def test_coordinate_single_war_room(self) -> None:
        plan = await self.service.coordinate([_state(WarRoomType.MATCH_DAY)])
        assert len(plan.active_war_room_ids) == 1
        assert plan.mode == CoordinationMode.PARALLEL

    async def test_coordinate_with_crisis_uses_priority_mode(self) -> None:
        states = [_state(WarRoomType.CRISIS), _state(WarRoomType.MATCH_DAY)]
        plan = await self.service.coordinate(states)
        assert plan.mode == CoordinationMode.PRIORITY_BASED

    async def test_coordinate_non_coexisting_publishes_conflict_event(self) -> None:
        # MATCH_DAY and TRANSFER_WINDOW cannot coexist
        states = [_state(WarRoomType.MATCH_DAY), _state(WarRoomType.TRANSFER_WINDOW)]
        await self.service.coordinate(states)
        history = get_event_bus().get_history("coordination_conflict_detected")
        assert len(history) >= 1

    async def test_resolve_conflict_crisis_wins_over_match_day(self) -> None:
        crisis = _state(WarRoomType.CRISIS, "WR-CRISIS-1")
        match_day = _state(WarRoomType.MATCH_DAY, "WR-MATCH-1")
        report = await self.service.resolve_conflict(crisis, match_day)
        assert isinstance(report, ConflictResolutionReport)
        assert report.winner_id == "WR-CRISIS-1"

    async def test_resolve_conflict_world_cup_wins_over_transfer(self) -> None:
        wc = _state(WarRoomType.WORLD_CUP, "WR-WC-1")
        tw = _state(WarRoomType.TRANSFER_WINDOW, "WR-TW-1")
        report = await self.service.resolve_conflict(wc, tw)
        assert report.winner_id == "WR-WC-1"

    async def test_route_event_returns_highest_priority(self) -> None:
        crisis = _state(WarRoomType.CRISIS, "WR-CRISIS-R")
        match_day = _state(WarRoomType.MATCH_DAY, "WR-MATCH-R")
        winner_id = await self.service.route_event("breaking_news_detected", [crisis, match_day])
        assert winner_id == "WR-CRISIS-R"

    async def test_route_event_empty_returns_none(self) -> None:
        result = await self.service.route_event("some_event", [])
        assert result is None

    async def test_allocate_divisions_assigns_all(self) -> None:
        states = [_state(WarRoomType.CRISIS), _state(WarRoomType.MATCH_DAY)]
        assignments = await self.service.allocate_divisions(states)
        assert isinstance(assignments, dict)
        assert len(assignments) > 0

    async def test_health_check(self) -> None:
        hc = self.service.health_check()
        assert hc["status"] == "healthy"
        assert hc["component"] == "cross_war_room_coordinator"
