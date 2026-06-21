"""Narrative Intelligence Node — tracks and analyzes football narrative lifecycles."""

from __future__ import annotations

import logging
from typing import Any

from sfc.graph.state import SFCState

logger = logging.getLogger("sfc.graph.nodes.narrative_intelligence_node")


async def narrative_intelligence_node(state: SFCState) -> dict[str, Any]:
    """Node: narrative_intelligence_node

    Detects active football narratives and tracks their lifecycle stages.
    Uses trend data from trend_radar_node as input signals.
    Results inform editorial and creative nodes.
    """
    trend_data = state.get("trend_radar_data", {})
    task_payload = state.get("task_payload", {})
    topics = task_payload.get("topics") or None

    logger.info("[NarrativeIntelligenceNode] Detecting narratives")

    try:
        from sfc.social.narrative.service import get_narrative_service

        service = get_narrative_service()
        narratives = await service.detect_narratives(
            topics=topics, trend_data=trend_data
        )
        report = await service.generate_report(narratives)
        narrative_data = report.to_dict()

        logger.info(
            "[NarrativeIntelligenceNode] Detected %d narratives | emerging=%d declining=%d",
            len(narratives),
            report.narrative_map.emerging_count,
            report.narrative_map.declining_count,
        )

        return {
            "narrative_intelligence_data": narrative_data,
            "pipeline_stage": "narrative_intelligence_complete",
        }

    except Exception as exc:
        logger.error("[NarrativeIntelligenceNode] Failed (non-fatal): %s", exc)
        return {
            "narrative_intelligence_data": {"error": str(exc)},
            "pipeline_stage": "narrative_intelligence_skipped",
            "warnings": [f"NARRATIVE_INTELLIGENCE_NODE_NON_FATAL: {exc}"],
        }
