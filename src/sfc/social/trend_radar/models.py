"""Trend Radar models — trend state, metrics, reports, and forecasts."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class TrendState(str, Enum):
    BREAKING = "breaking"
    EMERGING = "emerging"
    RISING = "rising"
    HOT = "hot"
    PEAK = "peak"
    DECLINING = "declining"
    DEAD = "dead"


class SocialSource(str, Enum):
    X = "x"
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"
    REDDIT = "reddit"
    GOOGLE_TRENDS = "google_trends"
    FORUMS = "forums"
    NEWS = "news"


class TrendMetrics(BaseModel):
    velocity: float = 0.0          # mentions per hour growth rate
    volume: int = 0                 # total mention count
    acceleration: float = 0.0      # change in velocity (2nd derivative)
    reach: int = 0                  # unique accounts reached
    engagement: float = 0.0        # average engagement rate (0-100)

    model_config = {"frozen": False}


class TrendForecast(BaseModel):
    expected_state_in_1h: TrendState = TrendState.EMERGING
    expected_state_in_6h: TrendState = TrendState.RISING
    expected_state_in_24h: TrendState = TrendState.DECLINING
    peak_estimate_hours: float = 6.0
    confidence: float = 0.0        # 0-100
    narrative: str = ""            # human-readable forecast

    model_config = {"frozen": False}


class TrendReport(BaseModel):
    trend_id: str = Field(default_factory=lambda: str(uuid4()))
    topic: str
    state: TrendState = TrendState.EMERGING
    metrics: TrendMetrics = Field(default_factory=TrendMetrics)
    score: float = 0.0             # 0-100 composite trend score
    platforms: list[str] = Field(default_factory=list)
    hashtags: list[str] = Field(default_factory=list)
    related_topics: list[str] = Field(default_factory=list)
    key_accounts: list[str] = Field(default_factory=list)
    forecast: TrendForecast = Field(default_factory=TrendForecast)
    recommendations: list[str] = Field(default_factory=list)
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def to_summary(self) -> dict[str, Any]:
        return {
            "trend_id": self.trend_id,
            "topic": self.topic,
            "state": self.state.value,
            "score": self.score,
            "velocity": self.metrics.velocity,
            "volume": self.metrics.volume,
        }


class TrendRadarSnapshot(BaseModel):
    snapshot_id: str = Field(default_factory=lambda: str(uuid4()))
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    breaking_trends: list[TrendReport] = Field(default_factory=list)
    emerging_trends: list[TrendReport] = Field(default_factory=list)
    hot_trends: list[TrendReport] = Field(default_factory=list)
    total_tracked: int = 0
    top_topic: str = ""
    top_score: float = 0.0
    alerts: list[str] = Field(default_factory=list)

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
