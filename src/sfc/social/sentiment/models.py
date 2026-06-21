"""Fan Sentiment Engine models — sentiment states, metrics, and reports."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class SentimentCategory(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class SentimentTarget(str, Enum):
    PLAYER = "player"
    COACH = "coach"
    CLUB = "club"
    COMPETITION = "competition"
    SPONSOR = "sponsor"
    NATIONAL_TEAM = "national_team"


class SentimentMetrics(BaseModel):
    score: float = 0.0          # -100 (very negative) to 100 (very positive)
    momentum: float = 0.0       # rate of change per hour
    volatility: float = 0.0     # standard deviation of recent scores
    confidence: float = 50.0    # 0-100 confidence in measurement
    sample_size: int = 0        # number of data points

    model_config = {"frozen": False}

    @property
    def category(self) -> SentimentCategory:
        if self.score > 20:
            return SentimentCategory.POSITIVE
        elif self.score < -20:
            return SentimentCategory.NEGATIVE
        return SentimentCategory.NEUTRAL


class SentimentTarget_(BaseModel):
    """A tracked entity with sentiment metrics."""
    entity_id: str = Field(default_factory=lambda: str(uuid4()))
    entity_name: str
    target_type: SentimentTarget = SentimentTarget.PLAYER
    metrics: SentimentMetrics = Field(default_factory=SentimentMetrics)
    recent_drivers: list[str] = Field(default_factory=list)   # what's causing sentiment
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class FanPulseReport(BaseModel):
    report_id: str = Field(default_factory=lambda: str(uuid4()))
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    tracked_entities: list[SentimentTarget_] = Field(default_factory=list)
    overall_score: float = 0.0      # weighted average across all entities
    overall_category: SentimentCategory = SentimentCategory.NEUTRAL
    alerts: list[str] = Field(default_factory=list)        # sentiment crises
    opportunities: list[str] = Field(default_factory=list) # positive moments
    ai_insights: str = ""

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def to_dashboard_data(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "overall_score": self.overall_score,
            "overall_category": self.overall_category.value,
            "entity_count": len(self.tracked_entities),
            "alerts": self.alerts,
            "opportunities": self.opportunities,
            "generated_at": self.generated_at.isoformat(),
        }
