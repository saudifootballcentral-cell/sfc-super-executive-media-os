"""Cost Forecasting Node — generates AI cost forecasts and budget alerts."""

from __future__ import annotations

import logging
from typing import Any

from sfc.graph.state import SFCState

logger = logging.getLogger("sfc.graph.nodes.cost_forecasting_node")


async def cost_forecasting_node(state: SFCState) -> dict[str, Any]:
    """Node: cost_forecasting_node

    Generates cost forecasts for daily, weekly, and monthly periods.
    Issues budget alerts if thresholds are exceeded.
    Provides optimization recommendations.

    Does NOT modify governance decisions or content approval status.
    """
    task_type = state.get("task_type", "")

    logger.info("[CostForecasting] Generating forecasts | task=%s", task_type)

    try:
        from sfc.forecasting.cost.service import get_cost_forecast_service, CostForecastService
        from sfc.forecasting.cost.models import ForecastPeriod

        service = get_cost_forecast_service()

        # Generate forecasts for all key periods
        forecasts: dict[str, Any] = {}
        alerts: list[str] = []
        recommendations: list[str] = []

        for period in [ForecastPeriod.DAILY, ForecastPeriod.WEEKLY, ForecastPeriod.MONTHLY]:
            forecast = service.forecast(period)
            forecasts[period.value] = {
                "forecast_usd": forecast.forecast_total_usd,
                "within_budget": forecast.within_budget,
                "utilization_pct": forecast.budget_utilization_pct,
                "run_rate_usd_per_day": forecast.run_rate_usd_per_day,
            }
            alerts.extend(forecast.budget_alerts)
            recommendations.extend(forecast.optimization_recommendations)

        # Deduplicate
        alerts = list(dict.fromkeys(alerts))
        recommendations = list(dict.fromkeys(recommendations))

        logger.info(
            "[CostForecasting] Forecasts generated | monthly=$%.6f alerts=%d",
            forecasts.get("monthly", {}).get("forecast_usd", 0),
            len(alerts),
        )

        return {
            "cost_forecast": {
                "forecasts": forecasts,
                "budget_alerts": alerts,
                "optimization_recommendations": recommendations,
            },
            "pipeline_stage": "cost_forecast_generated",
        }

    except Exception as exc:
        logger.error("[CostForecasting] Failed (non-fatal): %s", exc)
        return {
            "cost_forecast": {"error": str(exc)},
            "pipeline_stage": "cost_forecast_skipped",
            "warnings": [f"COST_FORECASTING_NON_FATAL: {exc}"],
        }
