"""Fan Sentiment Node — measures fan emotion across Saudi football entities."""

from __future__ import annotations

import logging
from typing import Any

from sfc.graph.state import SFCState

logger = logging.getLogger("sfc.graph.nodes.fan_sentiment_node")


async def fan_sentiment_node(state: SFCState) -> dict[str, Any]:
    """Node: fan_sentiment_node

    Analyzes fan sentiment for players, clubs, competitions, and national team.
    Detects sentiment crises and triggers war room evaluation.
    Results inform governance and narrative strategy.
    """
    task_payload = state.get("task_payload", {})
    entity_ids = task_payload.get("entity_ids") or None

    logger.info("[FanSentimentNode] Analyzing fan sentiment")

    try:
        from sfc.social.sentiment.service import get_sentiment_service

        service = get_sentiment_service()
        targets = await service.analyze(entity_ids=entity_ids, context=task_payload)
        report = await service.generate_fan_pulse_report(targets)
        sentiment_data = report.to_dict()

        alerts = await service.get_alerts()
        if alerts:
            logger.warning("[FanSentimentNode] %d sentiment alerts: %s", len(alerts), alerts[0])

        logger.info(
            "[FanSentimentNode] Sentiment analysis complete | entities=%d overall=%.1f category=%s",
            len(targets),
            report.overall_score,
            report.overall_category.value,
        )

        return {
            "fan_sentiment_data": sentiment_data,
            "pipeline_stage": "fan_sentiment_complete",
        }

    except Exception as exc:
        logger.error("[FanSentimentNode] Failed (non-fatal): %s", exc)
        return {
            "fan_sentiment_data": {"error": str(exc)},
            "pipeline_stage": "fan_sentiment_skipped",
            "warnings": [f"FAN_SENTIMENT_NODE_NON_FATAL: {exc}"],
        }
