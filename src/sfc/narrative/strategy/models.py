"""Narrative Strategy Engine models — actions, recommendations, and reports."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class StrategyAction(str, Enum):
    AMPLIFY = "amplify"
    SUPPORT = "support"
    MONITOR = "monitor"
    COUNTER = "counter"
    IGNORE = "ignore"
    REDIRECT = "redirect"
    DELAY = "delay"
    ACCELERATE = "accelerate"


class StrategyPriority(str, Enum):
    IMMEDIATE = "immediate"     # act now
    HIGH = "high"               # act within 2 hours
    MEDIUM = "medium"           # act within 24 hours
    LOW = "low"                 # schedule for later


class StrategyRecommendation(BaseModel):
    recommendation_id: str = Field(default_factory=lambda: str(uuid4()))
    narrative_id: str = ""
    narrative_title: str = ""
    action: StrategyAction
    priority: StrategyPriority = StrategyPriority.MEDIUM
    rationale: str = ""
    expected_outcome: str = ""
    confidence: float = 0.0         # 0-100
    effort_score: float = 50.0      # 0-100 (100 = high effort)
    impact_score: float = 0.0       # 0-100 expected impact
    personas_required: list[str] = Field(default_factory=list)
    action_steps: list[str] = Field(default_factory=list)
    success_metrics: list[str] = Field(default_factory=list)
    war_room_required: bool = False
    expires_in_hours: float | None = None

    model_config = {"frozen": False}

    @property
    def roi_score(self) -> float:
        if self.effort_score == 0:
            return 0.0
        return round(self.impact_score / self.effort_score * 100, 1)

    def to_dict(self) -> dict[str, Any]:
        return {**self.model_dump(mode="json"), "roi_score": self.roi_score}

    def to_summary(self) -> str:
        return (
            f"'{self.narrative_title}' — {self.action.value.upper()} [{self.priority.value}] "
            f"impact: {self.impact_score:.0f}, ROI: {self.roi_score:.0f}."
        )


class NarrativeStrategyReport(BaseModel):
    report_id: str = Field(default_factory=lambda: str(uuid4()))
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    recommendations: list[StrategyRecommendation] = Field(default_factory=list)
    top_recommendation: StrategyRecommendation | None = None
    immediate_actions: list[StrategyRecommendation] = Field(default_factory=list)
    by_action_type: dict[str, int] = Field(default_factory=dict)
    executive_summary: str = ""
    war_room_escalations: list[str] = Field(default_factory=list)

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
