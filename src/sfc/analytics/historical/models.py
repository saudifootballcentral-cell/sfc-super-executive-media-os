"""Historical analytics models — data points, trends, and forecasts."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class MetricType(str, Enum):
    REACH = "reach"
    ENGAGEMENT = "engagement"
    REVENUE = "revenue"
    PUBLISHING = "publishing"
    AI_COST = "ai_cost"
    PERSONA = "persona"
    WAR_ROOM = "war_room"
    SPONSOR = "sponsor"
    GROWTH = "growth"
    GOVERNANCE = "governance"


class HistoricalDataPoint(BaseModel):
    """A single metric observation at a point in time."""

    point_id: str = Field(default_factory=lambda: str(uuid4()))
    metric_type: MetricType
    metric_name: str
    value: float
    unit: str = ""
    recorded_at: datetime = Field(default_factory=datetime.utcnow)
    context: dict[str, Any] = Field(default_factory=dict)
    run_id: str = ""
    task_type: str = ""


class TrendDirection(str, Enum):
    UP = "up"
    DOWN = "down"
    STABLE = "stable"
    VOLATILE = "volatile"


class TrendReport(BaseModel):
    """Trend analysis across a set of data points."""

    report_id: str = Field(default_factory=lambda: str(uuid4()))
    metric_type: MetricType
    metric_name: str
    period_days: int
    data_points: int
    first_value: float
    last_value: float
    min_value: float
    max_value: float
    avg_value: float
    std_dev: float
    change_pct: float
    direction: TrendDirection
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    trend_data: list[dict[str, Any]] = Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class HistoricalComparison(BaseModel):
    """Compare two time periods for a metric."""

    metric_name: str
    period_a_label: str
    period_a_avg: float
    period_b_label: str
    period_b_avg: float
    change_pct: float
    is_improvement: bool
    generated_at: datetime = Field(default_factory=datetime.utcnow)
