"""Narrative Forecasting Engine models — horizon forecasts and scores."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ForecastHorizon(str, Enum):
    H24 = "24h"
    H72 = "72h"
    D7 = "7d"
    D30 = "30d"
    D90 = "90d"


class HorizonForecast(BaseModel):
    horizon: ForecastHorizon
    expected_growth: float = 0.0        # % growth expected
    expected_reach: int = 0
    expected_sentiment: float = 0.0     # -1.0 to 1.0
    expected_influence: float = 0.0     # 0-100
    expected_virality: float = 0.0      # 0-100
    peak_probability: float = 0.0       # probability of going viral
    confidence: float = 0.0            # 0.0-1.0 forecast confidence
    forecast_score: float = 0.0        # 0-100 composite

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class NarrativeForecast(BaseModel):
    forecast_id: str = Field(default_factory=lambda: str(uuid4()))
    narrative_id: str
    narrative_title: str = ""
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    horizons: dict[str, HorizonForecast] = Field(default_factory=dict)  # horizon → forecast
    overall_forecast_score: float = 0.0     # weighted composite
    forecast_narrative: str = ""             # AI-generated forecast text
    key_signals: list[str] = Field(default_factory=list)
    risk_signals: list[str] = Field(default_factory=list)
    opportunity_signals: list[str] = Field(default_factory=list)
    confidence: float = 0.0

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def to_summary(self) -> str:
        h24 = self.horizons.get(ForecastHorizon.H24.value)
        reach = f"{h24.expected_reach:,}" if h24 else "unknown"
        return (
            f"'{self.narrative_title}' — forecast score {self.overall_forecast_score:.0f}/100, "
            f"confidence {self.confidence:.0%}, 24h reach: {reach}."
        )


class ForecastBundle(BaseModel):
    bundle_id: str = Field(default_factory=lambda: str(uuid4()))
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    forecasts: list[NarrativeForecast] = Field(default_factory=list)
    top_forecast: NarrativeForecast | None = None
    highest_risk_forecast: NarrativeForecast | None = None
    highest_opportunity_forecast: NarrativeForecast | None = None
    avg_confidence: float = 0.0

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
