"""War Room Registry — single source of truth for all war room states."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

from sfc.war_rooms.registry.models import WarRoomDefinition
from sfc.war_rooms.shared.types import (
    WarRoomPriority,
    WarRoomState,
    WarRoomStatus,
    WarRoomType,
)

logger = logging.getLogger("sfc.war_rooms.registry")


class WarRoomRegistry:
    """Central registry of all war room definitions and active instances."""

    def __init__(self) -> None:
        self._definitions: dict[str, WarRoomDefinition] = {}  # war_room_type → definition
        self._active: dict[str, WarRoomState] = {}  # war_room_id → state
        self._history: list[WarRoomState] = []
        self._register_defaults()

    # ------------------------------------------------------------------
    # Bootstrap
    # ------------------------------------------------------------------

    def _register_defaults(self) -> None:
        """Register the 4 built-in war room types."""
        defaults = [
            WarRoomDefinition(
                war_room_id="def-match-day",
                name="Match Day War Room",
                war_room_type=WarRoomType.MATCH_DAY,
                default_priority=WarRoomPriority.P3_MEDIUM,
                default_divisions=["intelligence", "editorial", "creative", "publishing", "analytics", "governance"],
                activation_triggers=["match_scheduled", "match_triggered"],
                max_duration_hours=48,
                auto_deactivate=True,
                description="Activates 24h before kickoff; owns the complete match narrative.",
            ),
            WarRoomDefinition(
                war_room_id="def-world-cup",
                name="World Cup War Room",
                war_room_type=WarRoomType.WORLD_CUP,
                default_priority=WarRoomPriority.P1_CRITICAL,
                default_divisions=[
                    "strategic_planning", "intelligence", "editorial", "creative",
                    "publishing", "analytics", "revenue", "governance",
                ],
                activation_triggers=["world_cup_mode", "world_cup_triggered"],
                max_duration_hours=720,  # 30 days
                auto_deactivate=True,
                description="Maximum intensity; all divisions; P1 priority.",
            ),
            WarRoomDefinition(
                war_room_id="def-transfer-window",
                name="Transfer Window War Room",
                war_room_type=WarRoomType.TRANSFER_WINDOW,
                default_priority=WarRoomPriority.P3_MEDIUM,
                default_divisions=["intelligence", "editorial", "revenue", "governance"],
                activation_triggers=["transfer_window_open", "transfer_window_triggered"],
                max_duration_hours=336,  # 14 days typical window
                auto_deactivate=True,
                description="Market intelligence and rumor management.",
            ),
            WarRoomDefinition(
                war_room_id="def-crisis",
                name="Crisis Management War Room",
                war_room_type=WarRoomType.CRISIS,
                default_priority=WarRoomPriority.P1_CRITICAL,
                default_divisions=["intelligence", "editorial", "governance", "publishing"],
                activation_triggers=["crisis_detected", "crisis_triggered"],
                max_duration_hours=72,
                auto_deactivate=False,  # must be manually closed
                description="P1 — protect trust and reputation.",
            ),
        ]
        for definition in defaults:
            self._definitions[definition.war_room_type] = definition

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, definition: WarRoomDefinition) -> None:
        """Register or overwrite a war room definition."""
        self._definitions[definition.war_room_type] = definition
        logger.info("[Registry] Registered definition: %s", definition.name)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def activate(self, war_room_type: WarRoomType, metadata: dict[str, Any] | None = None) -> WarRoomState:
        """Create and activate a war room instance.

        Raises ValueError if a war room of this type is already active.
        """
        if metadata is None:
            metadata = {}

        # Check already active
        existing = self.get_by_type(war_room_type)
        if existing is not None:
            raise ValueError(
                f"War room of type {war_room_type} is already active: {existing.war_room_id}"
            )

        definition = self._definitions.get(war_room_type)
        if definition is None:
            raise ValueError(f"No definition found for war room type: {war_room_type}")

        war_room_id = f"WR-{war_room_type.value.upper()}-{uuid4().hex[:8].upper()}"
        state = WarRoomState(
            war_room_id=war_room_id,
            war_room_type=war_room_type,
            status=WarRoomStatus.ACTIVE,
            priority=definition.default_priority,
            owner="super_executive",
            activation_time=datetime.utcnow(),
            assigned_divisions=list(definition.default_divisions),
            metadata=metadata,
        )
        self._active[war_room_id] = state
        logger.info("[Registry] Activated war room: %s (%s)", war_room_id, war_room_type)
        return state

    def deactivate(self, war_room_id: str) -> WarRoomState:
        """Mark war room as closed, move to history."""
        state = self._active.get(war_room_id)
        if state is None:
            raise ValueError(f"No active war room found with id: {war_room_id}")

        state.status = WarRoomStatus.CLOSED
        state.deactivation_time = datetime.utcnow()
        self._history.append(state)
        del self._active[war_room_id]
        logger.info("[Registry] Deactivated war room: %s", war_room_id)
        return state

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_active(self) -> list[WarRoomState]:
        """Return all currently active war rooms."""
        return list(self._active.values())

    def get_by_type(self, war_room_type: WarRoomType) -> WarRoomState | None:
        """Return first active instance of given type."""
        for state in self._active.values():
            if state.war_room_type == war_room_type:
                return state
        return None

    def get_definition(self, war_room_type: WarRoomType) -> WarRoomDefinition | None:
        return self._definitions.get(war_room_type)

    def get_history(self) -> list[WarRoomState]:
        return list(self._history)

    # ------------------------------------------------------------------
    # State mutation
    # ------------------------------------------------------------------

    def update_state(self, war_room_id: str, **kwargs: Any) -> None:
        """Update fields on an active war room state."""
        state = self._active.get(war_room_id)
        if state is None:
            raise ValueError(f"No active war room found with id: {war_room_id}")
        for key, value in kwargs.items():
            if hasattr(state, key):
                setattr(state, key, value)
            else:
                logger.warning("[Registry] Unknown field on WarRoomState: %s", key)

    # ------------------------------------------------------------------
    # Health & reporting
    # ------------------------------------------------------------------

    def health_check(self) -> dict[str, Any]:
        return {
            "component": "war_room_registry",
            "status": "healthy",
            "active_count": len(self._active),
            "history_count": len(self._history),
            "definitions_registered": len(self._definitions),
            "active_war_rooms": [
                {"id": s.war_room_id, "type": s.war_room_type, "status": s.status}
                for s in self._active.values()
            ],
        }

    def status_report(self) -> dict[str, Any]:
        """Summary: active count, by priority, by type."""
        active = list(self._active.values())
        by_priority: dict[str, int] = {}
        by_type: dict[str, int] = {}
        for s in active:
            by_priority[s.priority] = by_priority.get(s.priority, 0) + 1
            by_type[s.war_room_type] = by_type.get(s.war_room_type, 0) + 1
        return {
            "active_count": len(active),
            "by_priority": by_priority,
            "by_type": by_type,
            "total_historical": len(self._history),
        }
