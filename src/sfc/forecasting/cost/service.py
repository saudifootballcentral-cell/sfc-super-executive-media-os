"""Cost Forecast Service — extends CostTracker with multi-period forecasting.

Reads session cost data from the existing CostTracker singleton and projects
costs forward. Generates budget alerts and optimization recommendations.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any

from sfc.forecasting.cost.models import CostForecast, ForecastPeriod, ProviderForecast

logger = logging.getLogger("sfc.forecasting.cost.service")

_PERIOD_DAYS: dict[ForecastPeriod, float] = {
    ForecastPeriod.DAILY: 1.0,
    ForecastPeriod.WEEKLY: 7.0,
    ForecastPeriod.MONTHLY: 30.0,
    ForecastPeriod.QUARTERLY: 90.0,
    ForecastPeriod.ANNUAL: 365.0,
}

_singleton: "CostForecastService | None" = None


def get_cost_forecast_service() -> "CostForecastService":
    global _singleton
    if _singleton is None:
        _singleton = CostForecastService()
    return _singleton


class CostForecastService:
    """Generates cost forecasts for all periods using live CostTracker data."""

    def __init__(self) -> None:
        self._forecasts: list[CostForecast] = []

    def forecast(self, period: ForecastPeriod = ForecastPeriod.MONTHLY) -> CostForecast:
        """Generate a cost forecast for the given period."""
        tracker_data = self._get_tracker_data()
        budget_limit = float(os.environ.get("MAX_DAILY_AI_COST", "100")) * _PERIOD_DAYS[period]
        daily_limit = float(os.environ.get("MAX_DAILY_AI_COST", "100"))

        run_rate = tracker_data.get("run_rate_usd_per_day", 0.0)
        period_days = _PERIOD_DAYS[period]
        forecast_total = run_rate * period_days

        utilization = (forecast_total / budget_limit * 100) if budget_limit > 0 else 0.0
        within = forecast_total <= budget_limit

        days_until_exhausted: float | None = None
        session_total = tracker_data.get("session_total_usd", 0.0)
        if run_rate > 0:
            remaining = daily_limit - session_total
            if remaining > 0:
                days_until_exhausted = remaining / run_rate
            else:
                days_until_exhausted = 0.0

        by_provider = tracker_data.get("by_provider_usd", {})
        by_model = tracker_data.get("by_model_usd", {})
        provider_forecasts = [
            ProviderForecast(
                provider=p,
                model="mixed",
                current_daily_usd=v,
                forecast_usd=v * period_days,
                forecast_period=period,
                calls_per_day=float(tracker_data.get("calls_per_day", 0)),
                tokens_per_call=float(tracker_data.get("avg_tokens_per_call", 0)),
            )
            for p, v in by_provider.items()
        ]

        alerts = self._build_alerts(forecast_total, budget_limit, utilization, daily_limit, session_total)
        recs = self._build_recommendations(
            utilization, by_model, tracker_data.get("fallback_rate_pct", 0.0)
        )

        forecast = CostForecast(
            period=period,
            run_rate_usd_per_day=round(run_rate, 6),
            forecast_total_usd=round(forecast_total, 6),
            budget_limit_usd=round(budget_limit, 2),
            budget_utilization_pct=round(utilization, 2),
            within_budget=within,
            days_until_budget_exhausted=days_until_exhausted,
            by_provider={p: round(v * period_days, 6) for p, v in by_provider.items()},
            by_model={m: round(v * period_days, 6) for m, v in by_model.items()},
            by_task_type={},
            provider_forecasts=provider_forecasts,
            budget_alerts=alerts,
            optimization_recommendations=recs,
            total_calls_this_session=tracker_data.get("total_calls", 0),
            fallback_rate_pct=tracker_data.get("fallback_rate_pct", 0.0),
        )
        self._forecasts.append(forecast)
        return forecast

    def forecast_all_periods(self) -> dict[str, Any]:
        """Generate forecasts for all periods."""
        results = {}
        for period in ForecastPeriod:
            f = self.forecast(period)
            results[period.value] = {
                "forecast_usd": f.forecast_total_usd,
                "within_budget": f.within_budget,
                "utilization_pct": f.budget_utilization_pct,
            }
        return results

    def get_history(self) -> list[dict[str, Any]]:
        return [f.to_dict() for f in self._forecasts[-50:]]

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _get_tracker_data(self) -> dict[str, Any]:
        try:
            from sfc.ai.cost_tracker import get_cost_tracker
            tracker = get_cost_tracker()
            report = tracker.get_report()
            session_total = report.get("session_total_usd", 0.0)
            total_calls = report.get("total_calls", 0)
            fallback_calls = report.get("fallback_calls", 0)
            fallback_rate = (fallback_calls / total_calls * 100) if total_calls > 0 else 0.0

            # Estimate run rate: calls in session mapped to daily estimate (assume 10 calls/run × 24 runs)
            est_daily_calls = max(total_calls * 24, 10)
            run_rate = session_total * 24 if session_total > 0 else 0.0

            return {
                "session_total_usd": session_total,
                "total_calls": total_calls,
                "fallback_calls": fallback_calls,
                "fallback_rate_pct": round(fallback_rate, 1),
                "run_rate_usd_per_day": round(run_rate, 6),
                "calls_per_day": est_daily_calls,
                "avg_tokens_per_call": report.get("avg_tokens_per_call", 0),
                "by_provider_usd": report.get("by_provider_usd", {}),
                "by_model_usd": report.get("by_model_usd", {}),
            }
        except Exception as exc:
            logger.debug("[CostForecast] CostTracker unavailable: %s", exc)
            return {
                "session_total_usd": 0.0,
                "total_calls": 0,
                "fallback_calls": 0,
                "fallback_rate_pct": 0.0,
                "run_rate_usd_per_day": 0.0,
                "calls_per_day": 0,
                "avg_tokens_per_call": 0,
                "by_provider_usd": {},
                "by_model_usd": {},
            }

    def _build_alerts(
        self,
        forecast: float,
        budget: float,
        utilization: float,
        daily_limit: float,
        session_total: float,
    ) -> list[str]:
        alerts: list[str] = []
        if utilization >= 100:
            alerts.append(f"BUDGET EXCEEDED — forecast ${forecast:.4f} > limit ${budget:.2f}")
        elif utilization >= 80:
            alerts.append(f"Budget at {utilization:.1f}% — approaching limit (${budget:.2f})")
        elif utilization >= 60:
            alerts.append(f"Budget at {utilization:.1f}% — monitor closely")
        if session_total >= daily_limit * 0.9:
            alerts.append(f"Daily limit nearly exhausted — ${session_total:.4f} of ${daily_limit:.2f} used")
        return alerts

    def _build_recommendations(
        self,
        utilization: float,
        by_model: dict[str, float],
        fallback_rate: float,
    ) -> list[str]:
        recs: list[str] = []
        if utilization > 50:
            recs.append("Switch non-critical tasks to claude-haiku to reduce costs")
        if fallback_rate < 100 and fallback_rate > 50:
            recs.append(f"High fallback rate ({fallback_rate:.0f}%) — check API key configuration")
        if fallback_rate == 100:
            recs.append("All calls using deterministic fallback — configure API keys for live AI")
        expensive = {m: v for m, v in by_model.items() if "opus" in m}
        if expensive:
            recs.append("Opus model usage detected — reserve for executive decisions only")
        if not recs:
            recs.append("AI cost within optimal range — no action required")
        return recs
