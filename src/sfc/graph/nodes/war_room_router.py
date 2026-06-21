"""War Room Router Node — activates the appropriate war room based on task_type.

Sits between super_executive and planning in the main pipeline.

Routing policy:
  task_type contains "crisis"     → CrisisWarRoom    (P1 Critical)
  task_type contains "world_cup"  → WorldCupWarRoom  (P1 Critical)
  task_type contains "match"      → MatchDayWarRoom  (P3 Medium)
  task_type contains "transfer"   → TransferWindowWarRoom (P3 Medium)
  task_type contains "breaking"   → BreakingNewsCommandCenter (ops, not war room)
  otherwise                       → no war room, continue to planning

Governance preservation: war_room_state is metadata only.
All content still flows through editorial → persona_layer → creative → governance → publishing.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sfc.graph.state import SFCState
from sfc.war_rooms.registry.service import WarRoomRegistry
from sfc.war_rooms.shared.types import WarRoomType

logger = logging.getLogger("sfc.graph.nodes.war_room_router")

# Task type keyword → WarRoomType (priority order: crisis first)
_TASK_TO_WAR_ROOM: list[tuple[str, WarRoomType]] = [
    ("crisis", WarRoomType.CRISIS),
    ("world_cup", WarRoomType.WORLD_CUP),
    ("match", WarRoomType.MATCH_DAY),
    ("transfer", WarRoomType.TRANSFER_WINDOW),
]

# Event types for activation_by_event compatibility
_WAR_ROOM_TO_EVENT: dict[WarRoomType, str] = {
    WarRoomType.CRISIS: "crisis_detected",
    WarRoomType.WORLD_CUP: "world_cup_mode",
    WarRoomType.MATCH_DAY: "match_scheduled",
    WarRoomType.TRANSFER_WINDOW: "transfer_window_open",
}

# Process-level registry singleton (shared across graph invocations)
_registry: WarRoomRegistry | None = None


def _get_registry() -> WarRoomRegistry:
    global _registry
    if _registry is None:
        _registry = WarRoomRegistry()
    return _registry


def _detect_war_room_type(task_type: str) -> WarRoomType | None:
    """Policy-driven detection of required war room from task_type."""
    task_lower = task_type.lower()
    for keyword, war_room_type in _TASK_TO_WAR_ROOM:
        if keyword in task_lower:
            return war_room_type
    return None


async def war_room_router_node(state: SFCState) -> dict[str, Any]:
    """Node: war_room_router

    Detects the task scenario and activates the appropriate war room.
    Sets war_room_state in pipeline state. Always continues to planning.

    Does NOT modify content_drafts, approved_content, or governance decisions.
    War room context is advisory metadata consumed by downstream nodes.
    """
    task_type = state.get("task_type", "")
    payload = state.get("task_payload", {})
    run_id = state.get("run_id", "")

    logger.info("[WarRoomRouter] Evaluating task_type=%s", task_type)

    # Check for breaking_news — activates BreakingNewsCommandCenter (not a war room)
    if "breaking" in task_type.lower():
        try:
            from sfc.war_rooms.operations.breaking_news.service import BreakingNewsCommandCenter
            center = BreakingNewsCommandCenter()
            await center.initialize()
            logger.info("[WarRoomRouter] BreakingNewsCommandCenter activated for task_type=%s", task_type)
            return {
                "war_room_state": {
                    "war_room_type": "breaking_news_command",
                    "war_room_id": None,
                    "activated": True,
                    "priority": "P2_HIGH",
                    "activation_time": datetime.utcnow().isoformat(),
                    "warnings": [],
                    "metadata": {"breaking_news_center": "active"},
                },
                "infrastructure_ready": True,
                "pipeline_stage": "war_room_routed",
            }
        except Exception as exc:
            logger.warning("[WarRoomRouter] BreakingNewsCommandCenter failed (non-fatal): %s", exc)
            return {
                "war_room_state": {
                    "war_room_type": "breaking_news_command",
                    "activated": False,
                    "priority": "P2_HIGH",
                    "warnings": [f"BreakingNewsCommandCenter init failed: {exc}"],
                },
                "pipeline_stage": "war_room_routed",
            }

    # Detect standard war room type
    war_room_type = _detect_war_room_type(task_type)

    if war_room_type is None:
        logger.info("[WarRoomRouter] No war room required for task_type=%s", task_type)
        return {
            "war_room_state": {
                "war_room_type": None,
                "war_room_id": None,
                "activated": False,
                "priority": None,
                "activation_time": None,
                "warnings": [],
            },
            "pipeline_stage": "war_room_routed",
        }

    # Activate via ActivationEngine
    try:
        from sfc.war_rooms.activation.service import ActivationEngine
        from sfc.war_rooms.activation.models import ActivationRequest, ActivationTrigger

        registry = _get_registry()
        engine = ActivationEngine(registry)

        event_type = _WAR_ROOM_TO_EVENT[war_room_type]
        result = await engine.activate_by_event(
            event_type,
            metadata={**payload, "run_id": run_id, "task_type": task_type},
        )

        if result is None:
            # activate_by_event returned None — no mapping found, do direct activation
            request = ActivationRequest(
                war_room_type=war_room_type,
                trigger=ActivationTrigger.EXECUTIVE_ACTIVATION,
                requester="war_room_router",
                metadata={"task_type": task_type, "run_id": run_id},
            )
            result = await engine.activate(request)

        if result.success:
            ws = result.war_room_state
            war_room_state = {
                "war_room_type": ws.war_room_type if ws else war_room_type.value,
                "war_room_id": ws.war_room_id if ws else result.war_room_id,
                "activated": True,
                "priority": ws.priority if ws else "P3_MEDIUM",
                "activation_time": result.activated_at.isoformat() if result.activated_at else datetime.utcnow().isoformat(),
                "warnings": result.warnings,
                "metadata": {"task_type": task_type, "run_id": run_id},
            }
            logger.info(
                "[WarRoomRouter] %s activated — id=%s",
                war_room_type.value,
                war_room_state.get("war_room_id"),
            )
        else:
            # Already active or failed — log and continue
            war_room_state = {
                "war_room_type": war_room_type.value,
                "war_room_id": result.war_room_id,
                "activated": False,
                "priority": "P3_MEDIUM",
                "activation_time": None,
                "warnings": result.reasons + result.warnings,
                "metadata": {"task_type": task_type},
            }
            logger.info(
                "[WarRoomRouter] %s not activated: %s",
                war_room_type.value,
                result.reasons,
            )

        return {
            "war_room_state": war_room_state,
            "infrastructure_ready": True,
            "pipeline_stage": "war_room_routed",
        }

    except Exception as exc:
        logger.error("[WarRoomRouter] Activation failed (non-fatal): %s", exc)
        return {
            "war_room_state": {
                "war_room_type": war_room_type.value if war_room_type else None,
                "war_room_id": None,
                "activated": False,
                "priority": None,
                "activation_time": None,
                "warnings": [f"War room activation failed: {exc}"],
            },
            "pipeline_stage": "war_room_routed",
            "warnings": [f"WAR_ROOM_ROUTER_NON_FATAL: {exc}"],
        }
