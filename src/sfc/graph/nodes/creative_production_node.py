"""LangGraph node — Creative Production Orchestrator."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("sfc.graph.nodes.creative_production")


async def creative_production_node(state: dict[str, Any]) -> dict[str, Any]:
    """Build production plan from intelligence context."""
    try:
        from sfc.creative.orchestrator.models import ProductionPriority, ProductionTrigger
        from sfc.creative.orchestrator.service import get_creative_production_orchestrator

        service = get_creative_production_orchestrator()
        narrative_context = str(state.get("narrative_models", {}).get("dominant_narrative", ""))
        trend_context = str(state.get("trend_radar_data", {}).get("top_trend", ""))
        war_room_active = bool(state.get("social_war_room_state", {}).get("active", False))

        trigger = ProductionTrigger.WAR_ROOM if war_room_active else ProductionTrigger.NARRATIVE
        priority = ProductionPriority.URGENT if war_room_active else ProductionPriority.HIGH

        plan = await service.create_production_plan(
            trigger=trigger,
            narrative_context=narrative_context,
            trend_context=trend_context,
            war_room_active=war_room_active,
            priority=priority,
            context=dict(state),
        )
        return {
            "production_plan": plan.to_dict(),
            "pipeline_stage": "creative_production",
        }
    except Exception as exc:
        logger.warning("creative_production_node failed: %s", exc)
        return {
            "production_plan": {},
            "pipeline_stage": "creative_production",
            "warnings": [f"creative_production_node: {exc}"],
        }
