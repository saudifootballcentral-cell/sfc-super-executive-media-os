"""Audience Segmentation Engine models — clusters, metrics, and reports."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class AudienceCluster(str, Enum):
    HARDCORE_FANS = "hardcore_fans"
    CASUAL_FANS = "casual_fans"
    MATCH_DAY_FANS = "match_day_fans"
    TRANSFER_FOLLOWERS = "transfer_followers"
    NATIONAL_TEAM_FANS = "national_team_fans"
    TACTICAL_ENTHUSIASTS = "tactical_enthusiasts"
    MEDIA_FOLLOWERS = "media_followers"
    SPONSOR_FOLLOWERS = "sponsor_followers"


class SegmentMetrics(BaseModel):
    size: int = 0
    engagement_rate: float = 0.0        # % of content engaged with
    influence_score: float = 0.0        # 0-100
    retention_rate: float = 0.0         # 0-100
    monthly_growth_rate: float = 0.0    # %
    avg_session_minutes: float = 0.0
    content_consumption_per_day: float = 0.0
    churn_risk: float = 0.0             # 0-100

    model_config = {"frozen": False}


class AudienceSegment(BaseModel):
    segment_id: str = Field(default_factory=lambda: str(uuid4()))
    cluster: AudienceCluster
    name: str = ""
    description: str = ""
    metrics: SegmentMetrics = Field(default_factory=SegmentMetrics)
    primary_platforms: list[str] = Field(default_factory=list)
    content_preferences: list[str] = Field(default_factory=list)
    narrative_sensitivity: dict[str, float] = Field(default_factory=dict)  # narrative_type → sensitivity
    peak_hours: list[int] = Field(default_factory=list)
    growth_opportunities: list[str] = Field(default_factory=list)
    targeting_recommendations: list[str] = Field(default_factory=list)

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def to_summary(self) -> str:
        return (
            f"{self.name} — {self.metrics.size:,} audience, "
            f"{self.metrics.engagement_rate:.1f}% engagement, "
            f"+{self.metrics.monthly_growth_rate:.1f}%/month growth."
        )


class AudienceSegmentReport(BaseModel):
    report_id: str = Field(default_factory=lambda: str(uuid4()))
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    segments: list[AudienceSegment] = Field(default_factory=list)
    total_audience: int = 0
    fastest_growing: AudienceCluster | None = None
    highest_engagement: AudienceCluster | None = None
    growth_opportunities: list[str] = Field(default_factory=list)
    targeting_recommendations: list[str] = Field(default_factory=list)
    ai_insights: str = ""

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
