"""Narrative Lifecycle Engine models — stages, health metrics, and reports."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class NarrativeStage(str, Enum):
    SEED = "seed"
    EMERGING = "emerging"
    GROWING = "growing"
    ACCELERATING = "accelerating"
    PEAK = "peak"
    DECLINING = "declining"
    DORMANT = "dormant"
    DEAD = "dead"


STAGE_ORDER = [
    NarrativeStage.SEED,
    NarrativeStage.EMERGING,
    NarrativeStage.GROWING,
    NarrativeStage.ACCELERATING,
    NarrativeStage.PEAK,
    NarrativeStage.DECLINING,
    NarrativeStage.DORMANT,
    NarrativeStage.DEAD,
]


class NarrativeHealthMetrics(BaseModel):
    velocity: float = 0.0           # mentions/hour growth rate
    acceleration: float = 0.0       # change in velocity
    volume: int = 0                 # total mentions
    influence: float = 0.0         # weighted influencer reach (0-100)
    reach: int = 0                  # estimated unique audience
    sentiment: float = 0.0          # -1.0 to 1.0
    health_score: float = 0.0       # 0-100 composite

    model_config = {"frozen": False}

    @property
    def is_healthy(self) -> bool:
        return self.health_score >= 60 and self.sentiment >= 40.0

    @property
    def is_at_risk(self) -> bool:
        return self.sentiment < 50.0 or self.health_score < 50.0


class NarrativeStageTransition(BaseModel):
    from_stage: NarrativeStage
    to_stage: NarrativeStage
    transitioned_at: datetime = Field(default_factory=datetime.utcnow)
    trigger: str = ""
    confidence: float = 0.8

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class NarrativeLifecycleReport(BaseModel):
    report_id: str = Field(default_factory=lambda: str(uuid4()))
    narrative_id: str
    narrative_title: str = ""
    current_stage: NarrativeStage = NarrativeStage.SEED
    metrics: NarrativeHealthMetrics = Field(default_factory=NarrativeHealthMetrics)
    stage_history: list[NarrativeStageTransition] = Field(default_factory=list)
    time_in_current_stage_hours: float = 0.0
    estimated_hours_to_next_stage: float | None = None
    next_stage_prediction: NarrativeStage | None = None
    lifecycle_forecast: str = ""
    alerts: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def to_summary(self) -> str:
        next_stage = self.next_stage_prediction.value if self.next_stage_prediction else "unknown"
        return (
            f"'{self.narrative_title}' is in {self.current_stage.value} stage "
            f"(health: {self.metrics.health_score:.0f}/100). "
            f"Next stage: {next_stage}."
        )


class LifecycleBatch(BaseModel):
    batch_id: str = Field(default_factory=lambda: str(uuid4()))
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    reports: list[NarrativeLifecycleReport] = Field(default_factory=list)
    peak_narratives: list[str] = Field(default_factory=list)      # narrative_ids at peak
    declining_narratives: list[str] = Field(default_factory=list)
    emerging_narratives: list[str] = Field(default_factory=list)
    total_active: int = 0

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
