"""Historical Analytics Node — records metrics and generates trend reports."""

from __future__ import annotations

import logging
from typing import Any

from sfc.graph.state import SFCState

logger = logging.getLogger("sfc.graph.nodes.historical_analytics_node")


async def historical_analytics_node(state: SFCState) -> dict[str, Any]:
    """Node: historical_analytics_node

    Records metrics from this pipeline run into the historical store
    and generates trend reports across tracked metrics.

    Does NOT modify governance decisions or content approval status.
    """
    task_type = state.get("task_type", "")
    run_id = state.get("run_id", "")

    logger.info("[HistoricalAnalytics] Recording metrics | task=%s run=%s", task_type, run_id)

    try:
        from sfc.analytics.historical.service import get_historical_service

        service = get_historical_service()

        # Record metrics from this run
        points = service.record_from_state(dict(state))

        # Generate trends for key metrics
        trends = service.get_all_trends(period_days=7)
        growth_report = service.get_growth_report()

        logger.info(
            "[HistoricalAnalytics] %d metrics recorded | %d trends tracked",
            len(points),
            len(trends),
        )

        return {
            "historical_analytics": {
                "metrics_recorded": len(points),
                "trends": [t.to_dict() for t in trends],
                "growth_report": growth_report,
                "total_data_points": service.get_data_count(),
            },
            "pipeline_stage": "historical_analytics_recorded",
        }

    except Exception as exc:
        logger.error("[HistoricalAnalytics] Failed (non-fatal): %s", exc)
        return {
            "historical_analytics": {"error": str(exc)},
            "pipeline_stage": "historical_analytics_skipped",
            "warnings": [f"HISTORICAL_ANALYTICS_NON_FATAL: {exc}"],
        }
