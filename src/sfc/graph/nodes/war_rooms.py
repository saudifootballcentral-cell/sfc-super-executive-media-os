"""War Room LangGraph node functions.

These nodes are NOT wired into the main pipeline by default.
They are activated conditionally by the super_executive when a war room
trigger is detected in the task payload.

Usage:
    result = await war_room_registry_node(state)
    result = await match_day_war_room_node(state)
"""

from __future__ import annotations

import logging
from typing import Any

from sfc.graph.state import SFCState
from sfc.war_rooms.registry.service import WarRoomRegistry
from sfc.war_rooms.shared.types import WarRoomType

logger = logging.getLogger("sfc.graph.nodes.war_rooms")

# Process-level registry singleton
_registry: WarRoomRegistry | None = None


def _get_registry() -> WarRoomRegistry:
    """Return process-level registry singleton."""
    global _registry
    if _registry is None:
        _registry = WarRoomRegistry()
    return _registry


async def war_room_registry_node(state: SFCState) -> dict[str, Any]:
    """Initialize/check war room registry. Returns war_room_status in state."""
    try:
        registry = _get_registry()
        active = registry.get_active()
        active_types = [w.war_room_type for w in active]
        warnings: list[str] = []
        if active:
            warnings.append(f"Active war rooms: {active_types}")
        return {
            "pipeline_stage": "war_room_registry_checked",
            "warnings": warnings,
        }
    except Exception as exc:
        logger.error("[WarRoomRegistry Node] Failed: %s", exc)
        return {
            "pipeline_stage": "war_room_registry_checked",
            "errors": [f"WAR_ROOM_REGISTRY: {exc}"],
        }


async def activation_engine_node(state: SFCState) -> dict[str, Any]:
    """Check task payload for war room triggers, activate if needed."""
    try:
        payload = state.get("task_payload", {})
        event_type = payload.get("war_room_trigger") or payload.get("event_type", "")

        if not event_type:
            return {"pipeline_stage": "activation_engine_checked", "warnings": []}

        from sfc.war_rooms.activation.service import ActivationEngine
        registry = _get_registry()
        engine = ActivationEngine(registry)
        result = await engine.activate_by_event(event_type, metadata=payload)

        if result is None:
            return {
                "pipeline_stage": "activation_engine_checked",
                "warnings": [f"No war room mapped for event: {event_type}"],
            }

        if result.success:
            return {
                "pipeline_stage": "activation_engine_activated",
                "warnings": result.warnings,
            }
        else:
            return {
                "pipeline_stage": "activation_engine_skipped",
                "warnings": result.reasons + result.warnings,
            }
    except Exception as exc:
        logger.error("[ActivationEngine Node] Failed: %s", exc)
        return {
            "pipeline_stage": "activation_engine_checked",
            "errors": [f"ACTIVATION_ENGINE: {exc}"],
        }


async def match_day_war_room_node(state: SFCState) -> dict[str, Any]:
    """Match Day War Room: create match brief and content plan."""
    try:
        from sfc.war_rooms.match_day.models import MatchInfo, MatchPhase
        from sfc.war_rooms.match_day.service import MatchDayWarRoom

        payload = state.get("task_payload", {})
        registry = _get_registry()
        war_room = MatchDayWarRoom(registry)

        match_info = MatchInfo(
            home_team=payload.get("home_team", "Home Team"),
            away_team=payload.get("away_team", "Away Team"),
            competition=payload.get("competition", "Saudi Pro League"),
            venue=payload.get("venue", ""),
        )

        await war_room.activate(match_info)
        brief = await war_room.create_match_brief(match_info)
        phase_str = payload.get("match_phase", "pre_match")
        try:
            phase = MatchPhase(phase_str)
        except ValueError:
            phase = MatchPhase.PRE_MATCH
        content_plan = await war_room.create_content_plan(match_info, phase)

        return {
            "pipeline_stage": "match_day_war_room_complete",
            "warnings": [],
            "intelligence_report": {
                **state.get("intelligence_report", {}),
                "match_brief": brief,
                "match_content_plan": content_plan,
            },
        }
    except Exception as exc:
        logger.error("[MatchDay Node] Failed: %s", exc)
        return {
            "pipeline_stage": "match_day_war_room_error",
            "errors": [f"MATCH_DAY_WAR_ROOM: {exc}"],
        }


async def world_cup_war_room_node(state: SFCState) -> dict[str, Any]:
    """World Cup War Room: daily brief and national team monitoring."""
    try:
        from sfc.war_rooms.world_cup.models import NationalTeamMonitor, WorldCupPhase
        from sfc.war_rooms.world_cup.service import WorldCupWarRoom

        payload = state.get("task_payload", {})
        registry = _get_registry()
        war_room = WorldCupWarRoom(registry)

        await war_room.activate(tournament_metadata=payload)
        team_monitor = await war_room.monitor_national_team(payload.get("match_data", {}))
        phase_str = payload.get("world_cup_phase", "pre_tournament")
        try:
            phase = WorldCupPhase(phase_str)
        except ValueError:
            phase = WorldCupPhase.PRE_TOURNAMENT
        brief = await war_room.create_daily_brief(phase, team_monitor)

        return {
            "pipeline_stage": "world_cup_war_room_complete",
            "warnings": [],
            "intelligence_report": {
                **state.get("intelligence_report", {}),
                "world_cup_brief": brief.model_dump(mode="json"),
            },
        }
    except Exception as exc:
        logger.error("[WorldCup Node] Failed: %s", exc)
        return {
            "pipeline_stage": "world_cup_war_room_error",
            "errors": [f"WORLD_CUP_WAR_ROOM: {exc}"],
        }


async def transfer_window_war_room_node(state: SFCState) -> dict[str, Any]:
    """Transfer Window War Room: ingest and classify transfer data."""
    try:
        from sfc.war_rooms.transfer_window.service import TransferWindowWarRoom

        payload = state.get("task_payload", {})
        registry = _get_registry()
        war_room = TransferWindowWarRoom(registry)

        window_type = payload.get("window_type", "summer")
        await war_room.activate(window_type=window_type)

        transfer_data = payload.get("transfer_data")
        result: dict[str, Any] = {"pipeline_stage": "transfer_window_war_room_complete"}

        if transfer_data:
            item = await war_room.ingest_transfer(transfer_data)
            alert = await war_room.create_executive_alert(item)
            brief = await war_room.create_transfer_brief()
            result["intelligence_report"] = {
                **state.get("intelligence_report", {}),
                "transfer_item": item.model_dump(mode="json"),
                "transfer_brief": brief,
                "executive_alert": alert,
            }
        else:
            brief = await war_room.create_transfer_brief()
            result["intelligence_report"] = {
                **state.get("intelligence_report", {}),
                "transfer_brief": brief,
            }
            result["warnings"] = ["No transfer_data in payload — returning empty brief."]

        return result
    except Exception as exc:
        logger.error("[TransferWindow Node] Failed: %s", exc)
        return {
            "pipeline_stage": "transfer_window_war_room_error",
            "errors": [f"TRANSFER_WINDOW_WAR_ROOM: {exc}"],
        }


async def crisis_war_room_node(state: SFCState) -> dict[str, Any]:
    """Crisis War Room: assess and create containment plan."""
    try:
        from sfc.war_rooms.crisis.models import CrisisEvent, CrisisSeverity, CrisisType
        from sfc.war_rooms.crisis.service import CrisisWarRoom

        payload = state.get("task_payload", {})
        registry = _get_registry()
        war_room = CrisisWarRoom(registry)

        # Build crisis event from payload
        try:
            crisis_type = CrisisType(payload.get("crisis_type", "reputation_risk"))
        except ValueError:
            crisis_type = CrisisType.REPUTATION_RISK
        try:
            severity = CrisisSeverity(payload.get("crisis_severity", "high"))
        except ValueError:
            severity = CrisisSeverity.HIGH

        crisis_event = CrisisEvent(
            crisis_type=crisis_type,
            severity=severity,
            description=payload.get("crisis_description", "Crisis detected — details under investigation"),
            detected_by=payload.get("detected_by", "system"),
            affected_content_ids=payload.get("affected_content_ids", []),
            affected_platforms=payload.get("affected_platforms", []),
        )

        await war_room.activate(crisis_event)
        report = await war_room.assess_crisis(crisis_event)
        alert = await war_room.create_executive_alert(crisis_event)

        return {
            "pipeline_stage": "crisis_war_room_complete",
            "warnings": [alert],
            "intelligence_report": {
                **state.get("intelligence_report", {}),
                "crisis_report": report.model_dump(mode="json"),
                "executive_alert": alert,
            },
        }
    except Exception as exc:
        logger.error("[Crisis Node] Failed: %s", exc)
        return {
            "pipeline_stage": "crisis_war_room_error",
            "errors": [f"CRISIS_WAR_ROOM: {exc}"],
        }
