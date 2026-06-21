"""Narrative Intelligence models — narrative states, metrics, and reports."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class NarrativeLifecycle(str, Enum):
    EMERGING = "emerging"
    GROWING = "growing"
    PEAKING = "peaking"
    DECLINING = "declining"
    DORMANT = "dormant"


class NarrativeCategory(str, Enum):
    PLAYER = "player"
    CLUB = "club"
    NATIONAL_TEAM = "national_team"
    TRANSFER = "transfer"
    TOURNAMENT = "tournament"
    REFEREE = "referee"
    SPONSOR = "sponsor"
    MEDIA = "media"
    GENERAL = "general"


class NarrativeMetrics(BaseModel):
    score: float = 0.0          # 0-100 narrative strength
    growth_rate: float = 0.0    # % growth per hour
    velocity: float = 0.0       # mentions per hour
    sentiment: float = 0.0      # -1.0 (negative) to 1.0 (positive)
    influence: float = 0.0      # weighted by influencer reach (0-100)
    reach: int = 0              # estimated unique reach

    model_config = {"frozen": False}


class Narrative(BaseModel):
    narrative_id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    description: str = ""
    lifecycle: NarrativeLifecycle = NarrativeLifecycle.EMERGING
    category: NarrativeCategory = NarrativeCategory.GENERAL
    entities: list[str] = Field(default_factory=list)   # players, clubs mentioned
    metrics: NarrativeMetrics = Field(default_factory=NarrativeMetrics)
    related_trends: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    key_accounts: list[str] = Field(default_factory=list)
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class NarrativeMap(BaseModel):
    map_id: str = Field(default_factory=lambda: str(uuid4()))
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    narratives: list[Narrative] = Field(default_factory=list)
    dominant_narrative: str = ""
    narrative_conflicts: list[dict[str, Any]] = Field(default_factory=list)
    emerging_count: int = 0
    declining_count: int = 0

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class NarrativeReport(BaseModel):
    report_id: str = Field(default_factory=lambda: str(uuid4()))
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    narrative_map: NarrativeMap = Field(default_factory=NarrativeMap)
    top_narratives: list[Narrative] = Field(default_factory=list)
    narrative_opportunities: list[str] = Field(default_factory=list)
    narrative_risks: list[str] = Field(default_factory=list)
    ai_insights: str = ""

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
