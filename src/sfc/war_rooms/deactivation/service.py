"""Deactivation Engine — safely closes war rooms and generates closure reports."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sfc.events.bus import get_event_bus
from sfc.war_rooms.deactivation.models import ClosureReport, DeactivationResult
from sfc.war_rooms.registry.service import WarRoomRegistry
from sfc.war_rooms.shared.events import WarRoomClosed
from sfc.war_rooms.shared.types import WarRoomMetrics, WarRoomState

logger = logging.getLogger("sfc.war_rooms.deactivation")


class DeactivationEngine:
    """Safely closes war rooms and generates structured closure reports."""

    def __init__(self, registry: WarRoomRegistry) -> None:
        self._registry = registry

    async def deactivate(self, war_room_id: str, reason: str = "completed") -> ClosureReport:
        """Safely close a war room and generate closure report."""
        state = self._registry._active.get(war_room_id)
        if state is None:
            raise ValueError(f"No active war room found with id: {war_room_id}")

        deactivated_at = datetime.utcnow()
        duration_minutes = 0.0
        if state.activation_time:
            duration_minutes = (deactivated_at - state.activation_time).total_seconds() / 60.0

        # 1. Collect metrics
        metrics = self._collect_metrics(state, duration_minutes)

        # 2. Extract lessons
        lessons = self._extract_lessons(state)

        # 3. Build closure report
        report = ClosureReport(
            war_room_id=war_room_id,
            war_room_type=str(state.war_room_type),
            activated_at=state.activation_time,
            deactivated_at=deactivated_at,
            duration_minutes=round(duration_minutes, 2),
            metrics=metrics,
            lessons_learned=lessons,
            decisions_made=[f"Deactivation reason: {reason}"],
            events_processed=len(state.active_events),
            final_status="closed",
        )

        # 4. Deactivate via registry
        try:
            self._registry.deactivate(war_room_id)
        except Exception as exc:
            logger.error("[Deactivation] Registry deactivation failed: %s", exc)

        # 5. Publish WarRoomClosed event
        try:
            bus = get_event_bus()
            bus.publish(
                WarRoomClosed(
                    division="deactivation_engine",
                    run_id=war_room_id,
                    payload={
                        "war_room_id": war_room_id,
                        "reason": reason,
                        "duration_minutes": duration_minutes,
                    },
                )
            )
        except Exception as exc:
            logger.warning("[Deactivation] Event publish failed (non-fatal): %s", exc)

        logger.info("[Deactivation] Closed war room %s after %.1f minutes", war_room_id, duration_minutes)
        return report

    async def auto_deactivate_expired(self) -> list[ClosureReport]:
        """Check for war rooms past their max_duration and deactivate them."""
        reports: list[ClosureReport] = []
        active = self._registry.get_active()
        now = datetime.utcnow()

        for state in active:
            definition = self._registry.get_definition(state.war_room_type)
            if definition is None or not definition.auto_deactivate:
                continue

            if state.activation_time is None:
                continue

            elapsed_hours = (now - state.activation_time).total_seconds() / 3600.0
            if elapsed_hours >= definition.max_duration_hours:
                logger.info(
                    "[Deactivation] Auto-deactivating expired war room %s (%.1fh >= %dh max)",
                    state.war_room_id, elapsed_hours, definition.max_duration_hours,
                )
                report = await self.deactivate(state.war_room_id, reason="auto_expired")
                reports.append(report)

        return reports

    def _collect_metrics(self, state: WarRoomState, duration_minutes: float) -> WarRoomMetrics:
        """Build metrics from state."""
        return WarRoomMetrics(
            war_room_id=state.war_room_id,
            content_pieces_produced=state.metadata.get("content_pieces_produced", 0),
            governance_pass_rate=state.metadata.get("governance_pass_rate", 0.0),
            avg_confidence_score=state.metadata.get("avg_confidence_score", 0.0),
            total_reach_estimate=state.metadata.get("total_reach_estimate", 0),
            escalations=len(state.escalations),
            errors=state.metadata.get("error_count", 0),
            duration_minutes=round(duration_minutes, 2),
            revenue_signals=state.metadata.get("revenue_signals", 0),
        )

    def _extract_lessons(self, state: WarRoomState) -> list[str]:
        """Extract lessons learned from war room state."""
        lessons: list[str] = []
        if state.escalations:
            lessons.append(f"{len(state.escalations)} escalation(s) occurred — review triggers.")
        if state.health_score < 80.0:
            lessons.append(f"Health score dropped to {state.health_score:.1f} — investigate root cause.")
        if len(state.active_events) > 10:
            lessons.append(f"High event volume ({len(state.active_events)}) — consider pre-staging resources.")
        if not lessons:
            lessons.append("Operations completed without significant incidents.")
        return lessons
