"""Opportunity Detection models — types, metrics, and reports."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class OpportunityType(str, Enum):
    CONTENT = "content"
    NARRATIVE = "narrative"
    SPONSOR = "sponsor"
    GROWTH = "growth"
    PARTNERSHIP = "partnership"
    AUDIENCE = "audience"


class OpportunityMetrics(BaseModel):
    impact: float = 0.0             # 0-100 business impact
    confidence: float = 0.0         # 0-100 confidence in detection
    speed: float = 0.0              # 0-100 time sensitivity (100 = act now)
    reach: int = 0                  # estimated audience reach
    revenue_potential: float = 0.0  # USD estimated

    model_config = {"frozen": False}

    @property
    def priority_score(self) -> float:
        return round(
            self.impact * 0.35 + self.confidence * 0.25 +
            self.speed * 0.25 + min(self.reach / 100_000, 15),
            1,
        )


class Opportunity(BaseModel):
    opportunity_id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    description: str = ""
    opportunity_type: OpportunityType = OpportunityType.CONTENT
    metrics: OpportunityMetrics = Field(default_factory=OpportunityMetrics)
    source_trend: str = ""
    source_narrative: str = ""
    executive_recommendation: str = ""
    required_personas: list[str] = Field(default_factory=list)
    action_steps: list[str] = Field(default_factory=list)
    expires_at: datetime | None = None
    detected_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def to_summary(self) -> dict[str, Any]:
        return {
            "opportunity_id": self.opportunity_id,
            "title": self.title,
            "type": self.opportunity_type.value,
            "priority_score": self.metrics.priority_score,
            "revenue_potential": self.metrics.revenue_potential,
        }


class OpportunityReport(BaseModel):
    report_id: str = Field(default_factory=lambda: str(uuid4()))
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    opportunities: list[Opportunity] = Field(default_factory=list)
    top_opportunity: Opportunity | None = None
    total_revenue_potential: float = 0.0
    by_type: dict[str, int] = Field(default_factory=dict)
    executive_summary: str = ""

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
