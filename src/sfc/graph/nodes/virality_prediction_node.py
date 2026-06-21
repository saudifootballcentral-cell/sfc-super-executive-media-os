"""Virality Prediction Node — forecasts content virality for current trends."""

from __future__ import annotations

import logging
from typing import Any

from sfc.graph.state import SFCState

logger = logging.getLogger("sfc.graph.nodes.virality_prediction_node")


async def virality_prediction_node(state: SFCState) -> dict[str, Any]:
    """Node: virality_prediction_node

    Forecasts virality potential for top trending topics.
    Recommends optimal formats, posting times, and hashtags.
    Results inform content strategy and creative direction.
    """
    trend_data = state.get("trend_radar_data", {})
    task_payload = state.get("task_payload", {})

    top_topic = trend_data.get("top_topic", "")
    top_score = trend_data.get("top_score", 50.0)
    platform = task_payload.get("platform", "x")

    logger.info("[ViralityPredictionNode] Forecasting virality for topic=%s", top_topic or "default")

    try:
        from sfc.social.virality.service import get_virality_engine

        engine = get_virality_engine()

        breaking_trends = trend_data.get("breaking_trends", [])
        topics_to_forecast = [top_topic] if top_topic else []
        for t in breaking_trends[:4]:
            if isinstance(t, dict):
                topic = t.get("topic", "")
                if topic and topic not in topics_to_forecast:
                    topics_to_forecast.append(topic)

        if not topics_to_forecast:
            topics_to_forecast = ["Saudi football news"]

        batch = await engine.forecast_batch(topics=topics_to_forecast, platform=platform)
        virality_data = batch.to_dict()

        logger.info(
            "[ViralityPredictionNode] Forecast complete | topics=%d avg_score=%.1f top_reach=%d",
            len(batch.forecasts),
            batch.avg_virality_score,
            batch.total_expected_reach,
        )

        return {
            "virality_forecast": virality_data,
            "pipeline_stage": "virality_prediction_complete",
        }

    except Exception as exc:
        logger.error("[ViralityPredictionNode] Failed (non-fatal): %s", exc)
        return {
            "virality_forecast": {"error": str(exc)},
            "pipeline_stage": "virality_prediction_skipped",
            "warnings": [f"VIRALITY_PREDICTION_NODE_NON_FATAL: {exc}"],
        }
