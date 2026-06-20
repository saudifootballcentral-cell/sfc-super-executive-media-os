"""Revenue Division — Pydantic models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from sfc.divisions.base import DivisionInput, DivisionOutput


class RevenueState(BaseModel):
    active_run_id: str | None = None
    active_campaigns: int = 0
    last_forecast_at: datetime | None = None


class RevenueInput(DivisionInput):
    pass


class RevenueOutput(DivisionOutput):
    revenue_signals: list[dict[str, Any]] = Field(default_factory=list)


class RevenueMetrics(BaseModel):
    total_opportunities_scored: int = 0
    avg_opportunity_score: float = 0.0
    total_forecasted_revenue_usd: float = 0.0


class RevenueMemoryReference(BaseModel):
    signals_key: str = ""
    forecast_key: str = ""
    run_id: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
