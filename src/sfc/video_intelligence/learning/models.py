"""Clip learning loop models."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field


class ClipPerformanceRecord(BaseModel):
    record_id: str = Field(default_factory=lambda: str(uuid4()))
    clip_id: str
    platform: str
    clip_type: str = ""
    views: int = 0
    likes: int = 0
    shares: int = 0
    comments: int = 0
    watch_time_seconds: float = 0.0
    engagement_rate: float = 0.0
    viral_score: float = 0.0
    predicted_score: float = 0.0
    prediction_error: float = 0.0
    recorded_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}

    @property
    def reached_viral(self) -> bool:
        return self.viral_score >= 80.0


class LearningInsight(BaseModel):
    insight_id: str = Field(default_factory=lambda: str(uuid4()))
    insight_type: str
    description: str
    data: dict = Field(default_factory=dict)
    confidence: float = 0.0
    action_recommendation: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}


class LearningReport(BaseModel):
    report_id: str = Field(default_factory=lambda: str(uuid4()))
    total_clips_tracked: int = 0
    avg_engagement_rate: float = 0.0
    top_clip_type: str = ""
    top_platform: str = ""
    insights: list[LearningInsight] = Field(default_factory=list)
    weight_adjustments: dict[str, float] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}
