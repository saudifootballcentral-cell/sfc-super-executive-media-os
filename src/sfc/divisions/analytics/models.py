"""Analytics Division — Pydantic models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from sfc.divisions.base import DivisionInput, DivisionOutput


class AnalyticsState(BaseModel):
    active_run_id: str | None = None
    last_report_at: datetime | None = None
    benchmark_cache: dict[str, Any] = Field(default_factory=dict)


class AnalyticsInput(DivisionInput):
    pass


class AnalyticsOutput(DivisionOutput):
    analytics_report: dict[str, Any] = Field(default_factory=dict)


class AnalyticsMetrics(BaseModel):
    total_reports_generated: int = 0
    avg_estimated_reach: float = 0.0
    avg_engagement_rate: float = 0.0


class AnalyticsMemoryReference(BaseModel):
    report_key: str = ""
    benchmark_key: str = ""
    run_id: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
