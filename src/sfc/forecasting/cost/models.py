"""Cost forecasting models — forecast periods, budgets, provider breakdowns."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ForecastPeriod(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


class ProviderForecast(BaseModel):
    """Per-provider cost forecast."""

    provider: str
    model: str
    current_daily_usd: float
    forecast_usd: float
    forecast_period: ForecastPeriod
    calls_per_day: float
    tokens_per_call: float


class CostForecast(BaseModel):
    """Full cost forecast across providers, models, and dimensions."""

    forecast_id: str = Field(default_factory=lambda: str(uuid4()))
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    period: ForecastPeriod
    run_rate_usd_per_day: float
    forecast_total_usd: float
    budget_limit_usd: float
    budget_utilization_pct: float
    within_budget: bool
    days_until_budget_exhausted: float | None = None

    # Breakdowns
    by_provider: dict[str, float] = Field(default_factory=dict)
    by_model: dict[str, float] = Field(default_factory=dict)
    by_task_type: dict[str, float] = Field(default_factory=dict)
    provider_forecasts: list[ProviderForecast] = Field(default_factory=list)

    # Optimization
    budget_alerts: list[str] = Field(default_factory=list)
    optimization_recommendations: list[str] = Field(default_factory=list)

    # Context
    total_calls_this_session: int = 0
    fallback_rate_pct: float = 0.0

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def to_markdown(self) -> str:
        lines = [
            f"# AI Cost Forecast — {self.period.value.capitalize()}",
            f"**Generated:** {self.generated_at.isoformat()}",
            "",
            f"## Summary",
            f"- Run rate: ${self.run_rate_usd_per_day:.4f}/day",
            f"- {self.period.value.capitalize()} forecast: **${self.forecast_total_usd:.4f}**",
            f"- Budget limit: ${self.budget_limit_usd:.2f}",
            f"- Utilization: {self.budget_utilization_pct:.1f}%",
            f"- Status: {'✅ Within budget' if self.within_budget else '⚠️ OVER BUDGET'}",
            "",
        ]
        if self.days_until_budget_exhausted is not None:
            lines.append(
                f"- Budget exhausted in: {self.days_until_budget_exhausted:.1f} days"
            )
        if self.by_provider:
            lines += ["## By Provider"]
            for provider, cost in self.by_provider.items():
                lines.append(f"- {provider}: ${cost:.4f}")
            lines.append("")
        if self.budget_alerts:
            lines += ["## Budget Alerts"] + [f"- ⚠️ {a}" for a in self.budget_alerts] + [""]
        if self.optimization_recommendations:
            lines += ["## Optimization Recommendations"]
            lines += [f"- {r}" for r in self.optimization_recommendations]
        return "\n".join(lines)
