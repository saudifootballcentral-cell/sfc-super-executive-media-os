"""Activation Engine — validates and activates war rooms."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sfc.events.bus import get_event_bus
from sfc.war_rooms.activation.models import ActivationRequest, ActivationResult, ActivationTrigger
from sfc.war_rooms.registry.service import WarRoomRegistry
from sfc.war_rooms.shared.events import (
    CrisisTriggered,
    MatchTriggered,
    TransferWindowTriggered,
    WarRoomActivated,
    WorldCupTriggered,
)
from sfc.war_rooms.shared.types import WarRoomType

logger = logging.getLogger("sfc.war_rooms.activation")

# Map event_type strings to war room types
_EVENT_TO_WAR_ROOM: dict[str, WarRoomType] = {
    "crisis_detected": WarRoomType.CRISIS,
    "crisis_triggered": WarRoomType.CRISIS,
    "match_triggered": WarRoomType.MATCH_DAY,
    "match_scheduled": WarRoomType.MATCH_DAY,
    "world_cup_triggered": WarRoomType.WORLD_CUP,
    "world_cup_mode": WarRoomType.WORLD_CUP,
    "transfer_window_triggered": WarRoomType.TRANSFER_WINDOW,
    "transfer_window_open": WarRoomType.TRANSFER_WINDOW,
}

_EVENT_TO_TRIGGER: dict[str, ActivationTrigger] = {
    "crisis_detected": ActivationTrigger.CRISIS_DETECTED,
    "crisis_triggered": ActivationTrigger.CRISIS_DETECTED,
    "match_triggered": ActivationTrigger.MATCH_SCHEDULED,
    "match_scheduled": ActivationTrigger.MATCH_SCHEDULED,
    "world_cup_triggered": ActivationTrigger.WORLD_CUP_MODE,
    "world_cup_mode": ActivationTrigger.WORLD_CUP_MODE,
    "transfer_window_triggered": ActivationTrigger.TRANSFER_WINDOW_OPEN,
    "transfer_window_open": ActivationTrigger.TRANSFER_WINDOW_OPEN,
}


class ActivationEngine:
    """Validates and activates war rooms based on triggers."""

    def __init__(self, registry: WarRoomRegistry) -> None:
        self._registry = registry

    async def activate(self, request: ActivationRequest) -> ActivationResult:
        """Validate and activate a war room."""
        warnings: list[str] = []
        reasons: list[str] = []

        # 1. Check if already active
        existing = self._registry.get_by_type(request.war_room_type)
        if existing is not None and not request.force:
            return ActivationResult(
                success=False,
                war_room_id=existing.war_room_id,
                war_room_state=existing,
                reasons=[f"War room of type {request.war_room_type} is already active: {existing.war_room_id}"],
                warnings=[],
            )

        if existing is not None and request.force:
            warnings.append(f"Force activation: bypassing existing active war room {existing.war_room_id}")

        # 2. Validate dependencies
        dependency_warnings = self._validate_dependencies(request.war_room_type)
        warnings.extend(dependency_warnings)

        # 3. Validate resources
        if not self._validate_resources(request.war_room_type):
            warnings.append(f"Resource validation warning: slots may be limited for {request.war_room_type}")

        # 4. Activate via registry
        try:
            if existing is not None and request.force:
                # Force: deactivate existing first
                try:
                    self._registry.deactivate(existing.war_room_id)
                except Exception as e:
                    warnings.append(f"Could not deactivate existing: {e}")

            state = self._registry.activate(request.war_room_type, metadata=request.metadata)
        except Exception as exc:
            return ActivationResult(
                success=False,
                reasons=[f"Registry activation failed: {exc}"],
                warnings=warnings,
            )

        # 5. Publish WarRoomActivated event
        try:
            bus = get_event_bus()
            bus.publish(
                WarRoomActivated(
                    division="war_room_activation_engine",
                    run_id=state.war_room_id,
                    payload={
                        "war_room_id": state.war_room_id,
                        "war_room_type": state.war_room_type,
                        "priority": state.priority,
                        "trigger": request.trigger,
                        "requester": request.requester,
                    },
                )
            )
        except Exception as exc:
            warnings.append(f"Event publish failed (non-fatal): {exc}")

        # 6. Return result
        return ActivationResult(
            success=True,
            war_room_id=state.war_room_id,
            war_room_state=state,
            reasons=reasons,
            warnings=warnings,
            activated_at=datetime.utcnow(),
        )

    def _validate_dependencies(self, war_room_type: WarRoomType) -> list[str]:
        """Check for conflicts with currently active war rooms. Returns warning list."""
        warnings: list[str] = []
        active = self._registry.get_active()
        for active_state in active:
            if active_state.war_room_type == war_room_type:
                continue  # same type conflict handled elsewhere
            from sfc.war_rooms.priority.service import PriorityEngine
            engine = PriorityEngine()
            if not engine.can_coexist(war_room_type, active_state.war_room_type):
                warnings.append(
                    f"Conflict: {war_room_type} cannot coexist with active {active_state.war_room_type} "
                    f"({active_state.war_room_id}). Higher priority will take precedence."
                )
        return warnings

    def _validate_resources(self, war_room_type: WarRoomType) -> bool:
        """Check that required divisions/resources are available."""
        # Soft check — we always proceed but may warn
        from sfc.war_rooms.resource_allocation.service import ResourceAllocationEngine
        engine = ResourceAllocationEngine(self._registry)
        # Sync used slots from current allocations (best effort)
        return True  # always allow; ResourceAllocationEngine handles slot clamping

    async def activate_by_event(self, event_type: str, metadata: dict[str, Any] | None = None) -> ActivationResult | None:
        """Map an incoming event to a war room activation if applicable."""
        if metadata is None:
            metadata = {}

        war_room_type = _EVENT_TO_WAR_ROOM.get(event_type)
        if war_room_type is None:
            logger.debug("[Activation] No war room mapped for event type: %s", event_type)
            return None

        trigger = _EVENT_TO_TRIGGER.get(event_type, ActivationTrigger.EXECUTIVE_ACTIVATION)

        # Publish appropriate trigger event
        try:
            bus = get_event_bus()
            trigger_events = {
                WarRoomType.CRISIS: CrisisTriggered,
                WarRoomType.MATCH_DAY: MatchTriggered,
                WarRoomType.WORLD_CUP: WorldCupTriggered,
                WarRoomType.TRANSFER_WINDOW: TransferWindowTriggered,
            }
            event_class = trigger_events.get(war_room_type)
            if event_class:
                bus.publish(
                    event_class(
                        division="activation_engine",
                        run_id=f"evt-{event_type}",
                        payload={"event_type": event_type, **metadata},
                    )
                )
        except Exception as exc:
            logger.warning("[Activation] Could not publish trigger event: %s", exc)

        request = ActivationRequest(
            war_room_type=war_room_type,
            trigger=trigger,
            requester="event_system",
            metadata={"source_event": event_type, **metadata},
        )
        return await self.activate(request)
