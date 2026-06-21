"""Opportunity Detection Node — identifies strategic content and business opportunities."""

from __future__ import annotations

import logging
from typing import Any

from sfc.graph.state import SFCState

logger = logging.getLogger("sfc.graph.nodes.opportunity_detection_node")


async def opportunity_detection_node(state: SFCState) -> dict[str, Any]:
    """Node: opportunity_detection_node

    Detects and scores strategic opportunities from aggregated social intelligence.
    Combines trend, narrative, sentiment, and audience signals.
    Results inform executive decision-making and revenue planning.
    """
    trend_data = state.get("trend_radar_data", {})
    narrative_data = state.get("narrative_intelligence_data", {})
    sentiment_data = state.get("fan_sentiment_data", {})
    audience_data = state.get("audience_intelligence_data", {})

    logger.info("[OpportunityDetectionNode] Detecting strategic opportunities")

    try:
        from sfc.social.opportunity.service import get_opportunity_engine

        engine = get_opportunity_engine()

        audience_summary = {
            "total_audience": audience_data.get("profile", {}).get("total_audience", 0)
        } if audience_data else {}

        opportunities = await engine.detect(
            trend_data=trend_data,
            narrative_data=narrative_data,
            sentiment_data=sentiment_data,
            audience_data=audience_summary,
        )
        report = await engine.generate_report(opportunities)
        opportunity_data = report.to_dict()

        logger.info(
            "[OpportunityDetectionNode] Detected %d opportunities | revenue_potential=$%.0f",
            len(opportunities),
            report.total_revenue_potential,
        )

        return {
            "opportunity_detections": [opportunity_data],
            "pipeline_stage": "opportunity_detection_complete",
        }

    except Exception as exc:
        logger.error("[OpportunityDetectionNode] Failed (non-fatal): %s", exc)
        return {
            "opportunity_detections": [{"error": str(exc)}],
            "pipeline_stage": "opportunity_detection_skipped",
            "warnings": [f"OPPORTUNITY_DETECTION_NODE_NON_FATAL: {exc}"],
        }
