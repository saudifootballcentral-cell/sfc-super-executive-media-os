"""Narrative Risk Engine models — risk types, scores, and reports."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class NarrativeRiskType(str, Enum):
    REPUTATION = "reputation"
    MISINFORMATION = "misinformation"
    MEDIA = "media"
    SPONSOR = "sponsor"
    FAN_BACKLASH = "fan_backlash"
    POLITICAL = "political"
    GOVERNANCE = "governance"


class RiskLevel(str, Enum):
    CRITICAL = "critical"     # score >= 80
    HIGH = "high"             # score >= 60
    MEDIUM = "medium"         # score >= 40
    LOW = "low"               # score < 40


class RiskScore(BaseModel):
    risk_type: NarrativeRiskType
    score: float = 0.0          # 0-100
    confidence: float = 0.0     # 0-100
    trend: str = "stable"       # rising | stable | falling
    evidence: list[str] = Field(default_factory=list)

    model_config = {"frozen": False}

    @property
    def level(self) -> RiskLevel:
        if self.score >= 80:
            return RiskLevel.CRITICAL
        if self.score >= 60:
            return RiskLevel.HIGH
        if self.score >= 40:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW

    def to_dict(self) -> dict[str, Any]:
        return {**self.model_dump(mode="json"), "level": self.level.value}


class MitigationRecommendation(BaseModel):
    recommendation_id: str = Field(default_factory=lambda: str(uuid4()))
    risk_type: NarrativeRiskType
    action: str
    rationale: str = ""
    priority: str = "MEDIUM"
    estimated_impact: float = 0.0   # 0-100 expected risk reduction
    personas_required: list[str] = Field(default_factory=list)
    time_to_implement: str = "immediate"

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class NarrativeRiskReport(BaseModel):
    report_id: str = Field(default_factory=lambda: str(uuid4()))
    narrative_id: str = ""
    narrative_title: str = ""
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    risk_scores: list[RiskScore] = Field(default_factory=list)
    overall_risk_score: float = 0.0     # 0-100
    overall_risk_level: RiskLevel = RiskLevel.LOW
    primary_risk: NarrativeRiskType | None = None
    mitigation_recommendations: list[MitigationRecommendation] = Field(default_factory=list)
    executive_alerts: list[str] = Field(default_factory=list)
    requires_war_room: bool = False
    ai_analysis: str = ""

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def to_summary(self) -> str:
        war_room = " [WAR ROOM REQUIRED]" if self.requires_war_room else ""
        return (
            f"'{self.narrative_title}' — {self.overall_risk_level.value.upper()} risk "
            f"({self.overall_risk_score:.0f}/100).{war_room}"
        )
