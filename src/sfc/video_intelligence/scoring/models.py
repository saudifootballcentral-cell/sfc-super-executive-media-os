"""Clip scoring models."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field


class PlatformScore(BaseModel):
    platform: str
    suitability_score: float = 0.0
    recommended_format: str = ""
    max_duration_seconds: float = 60.0
    within_duration_limit: bool = True

    model_config = {"frozen": False}


class ClipScore(BaseModel):
    score_id: str = Field(default_factory=lambda: str(uuid4()))
    clip_id: str
    viral_potential: float = 0.0
    audience_appeal: float = 0.0
    brand_alignment: float = 0.0
    technical_quality: float = 0.0
    overall_score: float = 0.0
    platform_scores: list[PlatformScore] = Field(default_factory=list)
    best_platform: str = ""
    recommended_clip_length: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}

    @property
    def is_publishable(self) -> bool:
        return self.overall_score >= 70.0 and self.brand_alignment >= 60.0

    def best_platform_score(self) -> PlatformScore | None:
        if not self.platform_scores:
            return None
        return max(self.platform_scores, key=lambda p: p.suitability_score)
