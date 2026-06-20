from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field

from sfc.personas.shared.types import PersonaMetrics


class EvaluationCriteria(BaseModel):
    accuracy_weight: float = 0.25
    relevance_weight: float = 0.20
    quality_weight: float = 0.25
    efficiency_weight: float = 0.15
    engagement_weight: float = 0.15


class PersonaScorecard(BaseModel):
    scorecard_id: str = Field(default_factory=lambda: f"SCORE-{uuid4().hex[:6].upper()}")
    persona_id: str
    metrics: PersonaMetrics
    overall_score: float
    grade: str
    improvement_areas: list[str]
    strengths: list[str]
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)


class PerformanceReport(BaseModel):
    report_id: str = Field(default_factory=lambda: f"PERF-{uuid4().hex[:6].upper()}")
    period: str
    scorecards: list[PersonaScorecard]
    top_performer_id: str | None
    recommendations: list[str]
    retirement_candidates: list[str]
    generated_at: datetime = Field(default_factory=datetime.utcnow)
