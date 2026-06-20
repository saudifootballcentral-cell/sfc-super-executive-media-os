"""Priority Engine — arbitrates conflicts between active war rooms."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from sfc.war_rooms.priority.models import ConflictType, PriorityDecision
from sfc.war_rooms.shared.types import WarRoomPriority, WarRoomState, WarRoomStatus, WarRoomType

if TYPE_CHECKING:
    from sfc.war_rooms.registry.service import WarRoomRegistry

logger = logging.getLogger("sfc.war_rooms.priority")

# Coexistence rules: pairs that ARE allowed to coexist
_ALLOWED_COEXIST: set[frozenset[WarRoomType]] = {
    frozenset({WarRoomType.WORLD_CUP, WarRoomType.TRANSFER_WINDOW}),
    frozenset({WarRoomType.WORLD_CUP, WarRoomType.MATCH_DAY}),
    # Crisis can coexist with everything
    frozenset({WarRoomType.CRISIS, WarRoomType.MATCH_DAY}),
    frozenset({WarRoomType.CRISIS, WarRoomType.WORLD_CUP}),
    frozenset({WarRoomType.CRISIS, WarRoomType.TRANSFER_WINDOW}),
}


class PriorityEngine:
    """
    Priority ordering: Crisis (P1) > World Cup (P1) > Match Day (P3) > Transfer Window (P3)
    Within same priority: newest activation wins.
    Executive override: always wins regardless of priority.
    """

    PRIORITY_ORDER: dict[WarRoomPriority, int] = {
        WarRoomPriority.P1_CRITICAL: 1,
        WarRoomPriority.P2_HIGH: 2,
        WarRoomPriority.P3_MEDIUM: 3,
        WarRoomPriority.P4_LOW: 4,
    }

    # Within P1, crisis takes precedence over world cup
    TYPE_ORDER: dict[WarRoomType, int] = {
        WarRoomType.CRISIS: 1,
        WarRoomType.WORLD_CUP: 2,
        WarRoomType.MATCH_DAY: 3,
        WarRoomType.TRANSFER_WINDOW: 4,
    }

    def assign_priority(self, war_room_type: WarRoomType) -> WarRoomPriority:
        """Return constitutional priority for a war room type."""
        mapping: dict[WarRoomType, WarRoomPriority] = {
            WarRoomType.CRISIS: WarRoomPriority.P1_CRITICAL,
            WarRoomType.WORLD_CUP: WarRoomPriority.P1_CRITICAL,
            WarRoomType.MATCH_DAY: WarRoomPriority.P3_MEDIUM,
            WarRoomType.TRANSFER_WINDOW: WarRoomPriority.P3_MEDIUM,
        }
        return mapping[war_room_type]

    def resolve_conflict(self, states: list[WarRoomState]) -> PriorityDecision | None:
        """Given multiple active war rooms, resolve any resource conflicts.

        Returns None if there is no conflict (all can coexist).
        """
        if len(states) <= 1:
            return None

        # Check if any pair cannot coexist
        conflicting: list[WarRoomState] = []
        for i, a in enumerate(states):
            for b in states[i + 1:]:
                if not self.can_coexist(a.war_room_type, b.war_room_type):
                    conflicting.extend([a, b])

        if not conflicting:
            return None

        # Find the winner (highest priority by type order, then newest activation)
        winner = self._select_winner(states)
        losers = [s for s in states if s.war_room_id != winner.war_room_id]

        return PriorityDecision(
            winner_war_room_id=winner.war_room_id,
            loser_war_room_ids=[s.war_room_id for s in losers],
            conflict_type=ConflictType.PRIORITY_CONFLICT,
            rationale=(
                f"{winner.war_room_type} (priority {winner.priority}) wins over "
                + ", ".join(s.war_room_type for s in losers)
            ),
        )

    def get_highest_priority(self, states: list[WarRoomState]) -> WarRoomState | None:
        """Return the highest-priority active war room."""
        if not states:
            return None
        return self._select_winner(states)

    def can_coexist(self, type_a: WarRoomType, type_b: WarRoomType) -> bool:
        """Check if two war room types can be active simultaneously."""
        if type_a == type_b:
            return False
        return frozenset({type_a, type_b}) in _ALLOWED_COEXIST

    def escalate(self, war_room_id: str, registry: "WarRoomRegistry", reason: str) -> None:
        """Mark a war room as escalated and update priority if needed."""
        try:
            state = registry._active.get(war_room_id)
            if state is None:
                logger.warning("[Priority] Cannot escalate — war room not found: %s", war_room_id)
                return

            escalation_record = {
                "reason": reason,
                "previous_status": state.status,
                "previous_priority": state.priority,
            }
            state.status = WarRoomStatus.ESCALATED
            state.escalations.append(escalation_record)

            # Escalate priority if not already at P1
            if state.priority != WarRoomPriority.P1_CRITICAL:
                state.priority = WarRoomPriority.P1_CRITICAL
                escalation_record["priority_upgraded"] = True

            logger.info("[Priority] Escalated war room %s: %s", war_room_id, reason)
        except Exception as exc:
            logger.error("[Priority] Escalation failed: %s", exc)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _select_winner(self, states: list[WarRoomState]) -> WarRoomState:
        """Select the highest-priority war room from a list."""
        def sort_key(s: WarRoomState) -> tuple[int, int, float]:
            type_rank = self.TYPE_ORDER.get(s.war_room_type, 99)
            # Newer activation time wins ties (use negative timestamp for ascending sort)
            activation_ts = s.activation_time.timestamp() if s.activation_time else 0.0
            return (type_rank, 0, -activation_ts)

        return sorted(states, key=sort_key)[0]
