"""Trend Radar Node — detects and classifies social media trends."""

from __future__ import annotations

import logging
from typing import Any

from sfc.graph.state import SFCState

logger = logging.getLogger("sfc.graph.nodes.trend_radar_node")


async def trend_radar_node(state: SFCState) -> dict[str, Any]:
    """Node: trend_radar_node

    Scans social platforms for trending Saudi football topics.
    Classifies trends by lifecycle state (Breaking/Emerging/Rising/Hot/Peak/Declining/Dead).
    Results feed into narrative and opportunity detection nodes.
    """
    task_payload = state.get("task_payload", {})
    topics = task_payload.get("topics") or None

    logger.info("[TrendRadarNode] Scanning for trends")

    try:
        from sfc.social.trend_radar.service import get_trend_radar

        service = get_trend_radar()
        snapshot = await service.scan(topics=topics)
        trend_data = snapshot.to_dict()

        if snapshot.alerts:
            logger.warning(
                "[TrendRadarNode] %d breaking trend alerts", len(snapshot.alerts)
            )

        logger.info(
            "[TrendRadarNode] Scan complete | tracked=%d top=%s score=%.1f",
            snapshot.total_tracked,
            snapshot.top_topic,
            snapshot.top_score,
        )

        return {
            "trend_radar_data": trend_data,
            "pipeline_stage": "trend_radar_complete",
        }

    except Exception as exc:
        logger.error("[TrendRadarNode] Failed (non-fatal): %s", exc)
        return {
            "trend_radar_data": {"error": str(exc)},
            "pipeline_stage": "trend_radar_skipped",
            "warnings": [f"TREND_RADAR_NODE_NON_FATAL: {exc}"],
        }
