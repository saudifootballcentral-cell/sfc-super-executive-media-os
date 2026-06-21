"""Influencer Intelligence Node — identifies and ranks key Saudi football influencers."""

from __future__ import annotations

import logging
from typing import Any

from sfc.graph.state import SFCState

logger = logging.getLogger("sfc.graph.nodes.influencer_intelligence_node")


async def influencer_intelligence_node(state: SFCState) -> dict[str, Any]:
    """Node: influencer_intelligence_node

    Scans Saudi football social ecosystem for key influencers.
    Ranks by composite score (influence, trust, reach, authority).
    Results inform content distribution and partnership strategy.
    """
    task_payload = state.get("task_payload", {})
    topic_filter = task_payload.get("topic_filter")

    logger.info("[InfluencerIntelligenceNode] Scanning influencer landscape")

    try:
        from sfc.social.influencer.service import get_influencer_service

        service = get_influencer_service()
        profiles = await service.scan(topic_filter=topic_filter)
        report = await service.generate_report(profiles)
        influencer_data = report.to_dict()

        if report.alerts:
            logger.info("[InfluencerIntelligenceNode] %d new influencer alerts", len(report.alerts))

        logger.info(
            "[InfluencerIntelligenceNode] Scan complete | tracked=%d new=%d",
            report.total_tracked,
            len(report.new_influencers),
        )

        return {
            "influencer_data": influencer_data,
            "pipeline_stage": "influencer_intelligence_complete",
        }

    except Exception as exc:
        logger.error("[InfluencerIntelligenceNode] Failed (non-fatal): %s", exc)
        return {
            "influencer_data": {"error": str(exc)},
            "pipeline_stage": "influencer_intelligence_skipped",
            "warnings": [f"INFLUENCER_INTELLIGENCE_NODE_NON_FATAL: {exc}"],
        }
