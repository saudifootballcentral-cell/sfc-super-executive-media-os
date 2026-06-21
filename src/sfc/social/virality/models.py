"""Virality Prediction models — forecasts, metrics, and recommendations."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ContentFormat(str, Enum):
    SHORT_VIDEO = "short_video"
    LONG_VIDEO = "long_video"
    IMAGE = "image"
    CAROUSEL = "carousel"
    TEXT = "text"
    LIVE = "live"
    STORY = "story"
    THREAD = "thread"


class ViralityTier(str, Enum):
    VIRAL = "viral"         # >1M projected reach
    HIGH = "high"           # >100k projected reach
    MEDIUM = "medium"       # >10k projected reach
    LOW = "low"             # <10k projected reach


class ViralityMetrics(BaseModel):
    virality_score: float = 0.0         # 0-100
    probability: float = 0.0            # 0.0-1.0 probability of going viral
    expected_reach: int = 0
    expected_engagement: float = 0.0    # total engagements
    expected_shares: int = 0
    expected_views: int = 0
    expected_watch_time_seconds: float = 0.0
    expected_follower_growth: int = 0

    model_config = {"frozen": False}

    @property
    def tier(self) -> ViralityTier:
        if self.expected_reach >= 1_000_000:
            return ViralityTier.VIRAL
        elif self.expected_reach >= 100_000:
            return ViralityTier.HIGH
        elif self.expected_reach >= 10_000:
            return ViralityTier.MEDIUM
        return ViralityTier.LOW


class ViralityForecast(BaseModel):
    forecast_id: str = Field(default_factory=lambda: str(uuid4()))
    content_type: str = ""
    content_format: ContentFormat = ContentFormat.SHORT_VIDEO
    platform: str = ""
    topic: str = ""
    metrics: ViralityMetrics = Field(default_factory=ViralityMetrics)
    optimal_post_time: str = "18:00 UTC"
    optimal_hashtags: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    optimization_tips: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def to_summary(self) -> dict[str, Any]:
        return {
            "forecast_id": self.forecast_id,
            "topic": self.topic,
            "platform": self.platform,
            "virality_score": self.metrics.virality_score,
            "expected_reach": self.metrics.expected_reach,
            "tier": self.metrics.tier.value,
        }


class ViralityBatch(BaseModel):
    batch_id: str = Field(default_factory=lambda: str(uuid4()))
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    forecasts: list[ViralityForecast] = Field(default_factory=list)
    top_forecast: ViralityForecast | None = None
    avg_virality_score: float = 0.0
    total_expected_reach: int = 0

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
