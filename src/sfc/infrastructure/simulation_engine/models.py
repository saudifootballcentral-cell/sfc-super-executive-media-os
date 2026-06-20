"""Models for the Simulation Engine infrastructure service."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field


class SimulationScenario(BaseModel):
    """Input scenario for simulation."""

    scenario_id: str = Field(default_factory=lambda: f"SIM-{uuid4().hex[:6].upper()}")
    name: str
    content_type: str
    platforms: list[str]
    task_type: str
    timing: str = "standard"
    confidence_score: float = 85.0
    source_count: int = 2


class SimulationResult(BaseModel):
    """Output of a single simulation run."""

    scenario_id: str
    expected_reach: int
    expected_engagement_rate: float
    expected_watch_time_minutes: int
    expected_revenue_usd: float
    virality_score: float       # 0-100
    risk_score: float           # 0-100
    strategic_value: float      # 0-100
    overall_score: float        # composite 0-100
    confidence: float           # model confidence 0-100
    simulated_at: datetime = Field(default_factory=datetime.utcnow)


class SimulationComparison(BaseModel):
    """Comparison of multiple simulation results."""

    scenarios: list[SimulationResult]
    recommended_scenario_id: str
    recommendation_rationale: str
    compared_at: datetime = Field(default_factory=datetime.utcnow)
