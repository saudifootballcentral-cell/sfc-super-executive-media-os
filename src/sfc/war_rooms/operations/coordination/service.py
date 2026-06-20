"""Cross War Room Coordinator — service implementation."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sfc.events.bus import get_event_bus
from sfc.war_rooms.operations.coordination.models import (
    ConflictResolutionReport,
    ConflictType,
    CoordinationMode,
    CoordinationPlan,
)
from sfc.war_rooms.priority.service import PriorityEngine
from sfc.war_rooms.shared.events import CoordinationConflictDetected
from sfc.war_rooms.shared.types import WarRoomState, WarRoomType

logger = logging.getLogger("sfc.war_rooms.operations.coordination")

# Priority type order: lower = higher priority
_TYPE_ORDER: dict[WarRoomType, int] = {
    WarRoomType.CRISIS: 1,
    WarRoomType.WORLD_CUP: 2,
    WarRoomType.MATCH_DAY: 3,
    WarRoomType.TRANSFER_WINDOW: 4,
}

_ALL_DIVISIONS = [
    "intelligence", "editorial", "creative", "publishing",
    "analytics", "governance", "revenue", "strategic_planning",
]


class CrossWarRoomCoordinator:
    """Coordinates multiple simultaneously active war rooms."""

    def __init__(self) -> None:
        self._priority_engine = PriorityEngine()

    async def coordinate(self, active_states: list[WarRoomState]) -> CoordinationPlan:
        """Build a coordination plan for all currently active war rooms."""
        if not active_states:
            return CoordinationPlan(
                active_war_room_ids=[],
                mode=CoordinationMode.PARALLEL,
                division_assignments={},
                event_routing={},
                resource_split={},
            )

        # Determine coordination mode
        has_crisis = any(s.war_room_type == WarRoomType.CRISIS for s in active_states)
        if len(active_states) == 1:
            mode = CoordinationMode.PARALLEL
        elif has_crisis:
            mode = CoordinationMode.PRIORITY_BASED
        else:
            mode = CoordinationMode.PARALLEL

        # Check for conflicts
        conflict_pairs: list[tuple[WarRoomState, WarRoomState]] = []
        for i, a in enumerate(active_states):
            for b in active_states[i + 1:]:
                if not self._priority_engine.can_coexist(a.war_room_type, b.war_room_type):
                    conflict_pairs.append((a, b))

        if conflict_pairs:
            get_event_bus().publish(
                CoordinationConflictDetected(
                    division="operations",
                    run_id="coordination-conflict",
                    payload={
                        "conflict_count": len(conflict_pairs),
                        "war_room_ids": [s.war_room_id for s in active_states],
                    },
                )
            )
            logger.warning("[Coordination] %d conflict(s) detected", len(conflict_pairs))

        division_assignments = await self.allocate_divisions(active_states)
        event_routing = {s.war_room_id: s.war_room_type.value for s in active_states}
        resource_split = {
            s.war_room_id: round(100.0 / len(active_states), 1) for s in active_states
        }

        return CoordinationPlan(
            active_war_room_ids=[s.war_room_id for s in active_states],
            mode=mode,
            division_assignments=division_assignments,
            event_routing=event_routing,
            resource_split=resource_split,
            created_at=datetime.utcnow(),
        )

    async def resolve_conflict(
        self,
        state_a: WarRoomState,
        state_b: WarRoomState,
    ) -> ConflictResolutionReport:
        """Resolve a conflict between two war rooms using priority type order."""
        order_a = _TYPE_ORDER.get(state_a.war_room_type, 99)
        order_b = _TYPE_ORDER.get(state_b.war_room_type, 99)

        if order_a <= order_b:
            winner, loser = state_a, state_b
        else:
            winner, loser = state_b, state_a

        report = ConflictResolutionReport(
            conflict_type=ConflictType.PRIORITY_CONFLICT,
            war_room_ids=[state_a.war_room_id, state_b.war_room_id],
            winner_id=winner.war_room_id,
            rationale=(
                f"{winner.war_room_type.value} (rank {_TYPE_ORDER.get(winner.war_room_type, 99)}) "
                f"outranks {loser.war_room_type.value} (rank {_TYPE_ORDER.get(loser.war_room_type, 99)})"
            ),
            resolved_at=datetime.utcnow(),
        )
        logger.info("[Coordination] Conflict resolved: winner=%s", winner.war_room_id)
        return report

    async def route_event(
        self,
        event_type: str,
        active_states: list[WarRoomState],
    ) -> str | None:
        """Return the war_room_id of the highest-priority active room to handle the event."""
        if not active_states:
            return None
        winner = self._priority_engine.get_highest_priority(active_states)
        return winner.war_room_id if winner else None

    async def allocate_divisions(
        self, active_states: list[WarRoomState]
    ) -> dict[str, str]:
        """Map each division to the war_room_id that owns it (winner for contested ones)."""
        if not active_states:
            return {}

        # Sort states by type priority (ascending = higher priority first)
        sorted_states = sorted(
            active_states, key=lambda s: _TYPE_ORDER.get(s.war_room_type, 99)
        )

        assignments: dict[str, str] = {}
        for state in sorted_states:
            for division in state.assigned_divisions:
                # First assignment wins (highest priority war room already first)
                if division not in assignments:
                    assignments[division] = state.war_room_id

        # Assign any uncontested global divisions to the highest priority war room
        if sorted_states:
            top_id = sorted_states[0].war_room_id
            for division in _ALL_DIVISIONS:
                if division not in assignments:
                    assignments[division] = top_id

        return assignments

    def health_check(self) -> dict[str, Any]:
        return {
            "component": "cross_war_room_coordinator",
            "status": "healthy",
        }
