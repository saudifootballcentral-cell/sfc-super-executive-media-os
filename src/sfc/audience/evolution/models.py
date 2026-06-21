"""Audience Evolution Engine models — behavior change, growth, and retention forecasts."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class EvolutionDriver(str, Enum):
    NARRATIVE_ADOPTION = "narrative_adoption"
    PLATFORM_MIGRATION = "platform_migration"
    BEHAVIOR_CHANGE = "behavior_change"
    INTEREST_SHIFT = "interest_shift"
    ENGAGEMENT_TREND = "engagement_trend"


class EvolutionTrend(BaseModel):
    trend_id: str = Field(default_factory=lambda: str(uuid4()))
    driver: EvolutionDriver
    segment_id: str = ""
    direction: str = "growing"      # growing | stable | declining
    magnitude: float = 0.0          # 0-100 strength of change
    confidence: float = 0.0         # 0-100
    description: str = ""
    detected_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class GrowthForecast(BaseModel):
    segment_id: str = ""
    segment_name: str = ""
    current_size: int = 0
    forecast_30d: int = 0
    forecast_90d: int = 0
    forecast_365d: int = 0
    growth_rate_monthly: float = 0.0
    confidence: float = 0.0
    key_drivers: list[str] = Field(default_factory=list)

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class RetentionForecast(BaseModel):
    segment_id: str = ""
    current_retention: float = 0.0      # %
    forecast_30d_retention: float = 0.0
    forecast_90d_retention: float = 0.0
    churn_risk_score: float = 0.0       # 0-100
    at_risk_count: int = 0
    retention_actions: list[str] = Field(default_factory=list)

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class AudienceEvolutionReport(BaseModel):
    report_id: str = Field(default_factory=lambda: str(uuid4()))
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    evolution_trends: list[EvolutionTrend] = Field(default_factory=list)
    growth_forecasts: list[GrowthForecast] = Field(default_factory=list)
    retention_forecasts: list[RetentionForecast] = Field(default_factory=list)
    platform_migration_signals: dict[str, str] = Field(default_factory=dict)  # from → to
    narrative_adoption_rates: dict[str, float] = Field(default_factory=dict)  # narrative_id → rate
    total_projected_growth: int = 0
    high_churn_risk_segments: list[str] = Field(default_factory=list)
    ai_insights: str = ""

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
