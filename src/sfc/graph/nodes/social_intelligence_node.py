"""Social Intelligence Node — orchestrates full social intelligence scan."""

from __future__ import annotations

import logging
from typing import Any

from sfc.graph.state import SFCState

logger = logging.getLogger("sfc.graph.nodes.social_intelligence_node")


async def social_intelligence_node(state: SFCState) -> dict[str, Any]:
    """Node: social_intelligence_node

    Runs a full social intelligence scan covering trends, narratives, sentiment,
    influencers, virality, audience, opportunities, and knowledge graph.
    Results are read-only analytics — no content is published from this node.
    """
    task_type = state.get("task_type", "")
    task_payload = state.get("task_payload", {})

    logger.info("[SocialIntelligenceNode] Starting social scan | task=%s", task_type)

    try:
        from sfc.social.center import get_social_center

        center = get_social_center()
        topics = task_payload.get("topics") or None

        scan_result = await center.run_full_scan(topics=topics, context=task_payload)

        logger.info("[SocialIntelligenceNode] Full scan complete")

        return {
            "social_intelligence_report": scan_result,
            "trend_radar_data": scan_result.get("trend_radar", {}),
            "narrative_intelligence_data": scan_result.get("narrative_intelligence", {}),
            "fan_sentiment_data": scan_result.get("fan_sentiment", {}),
            "influencer_data": scan_result.get("influencer_intelligence", {}),
            "audience_intelligence_data": scan_result.get("audience_intelligence", {}),
            "opportunity_detections": [scan_result.get("opportunity_detections", {})],
            "social_knowledge_snapshot": scan_result.get("knowledge_snapshot", {}),
            "social_war_room_state": {"alerts": scan_result.get("war_room_alerts", [])},
            "pipeline_stage": "social_intelligence_complete",
        }

    except Exception as exc:
        logger.error("[SocialIntelligenceNode] Failed (non-fatal): %s", exc)
        return {
            "social_intelligence_report": {"error": str(exc)},
            "pipeline_stage": "social_intelligence_skipped",
            "warnings": [f"SOCIAL_INTELLIGENCE_NODE_NON_FATAL: {exc}"],
        }
