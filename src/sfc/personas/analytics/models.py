from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field

from sfc.personas.shared.types import PersonaCategory


class AnalyticsPeriod(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    SESSION = "session"


class PersonaRanking(BaseModel):
    rank: int
    persona_id: str
    persona_name: str
    overall_score: float
    category: PersonaCategory
    trend: str = "stable"


class PerformanceDashboard(BaseModel):
    dashboard_id: str = Field(default_factory=lambda: f"DASH-{uuid4().hex[:6].upper()}")
    period: AnalyticsPeriod
    total_personas: int
    active_personas: int
    avg_performance_score: float
    top_performer: PersonaRanking | None
    rankings: list[PersonaRanking]
    category_breakdown: dict[str, float]
    optimization_recommendations: list[str]
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class OptimizationRecommendation(BaseModel):
    persona_id: str
    current_score: float
    target_score: float
    actions: list[str]
    priority: str = "medium"
