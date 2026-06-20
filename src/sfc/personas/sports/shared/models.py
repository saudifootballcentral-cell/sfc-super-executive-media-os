"""Shared models for Sports Intelligence Personas."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class InsightType(str, Enum):
    ANALYSIS = "analysis"
    REPORT = "report"
    ALERT = "alert"
    RECOMMENDATION = "recommendation"
    BRIEF = "brief"
    PREDICTION = "prediction"


class InsightConfidence(str, Enum):
    HIGH = "high"        # >= 85
    MEDIUM = "medium"    # 65-84
    LOW = "low"          # < 65


class PersonaInsight(BaseModel):
    insight_id: str = Field(default_factory=lambda: f"INSIGHT-{uuid4().hex[:8].upper()}")
    persona_id: str
    persona_name: str
    insight_type: InsightType
    title: str
    summary: str
    key_findings: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    confidence_score: float = 80.0
    confidence_level: InsightConfidence = InsightConfidence.MEDIUM
    sources_used: list[str] = Field(default_factory=list)
    entities_mentioned: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class PersonaKnowledgeState(BaseModel):
    persona_id: str
    domain: str
    known_entities: list[str] = Field(default_factory=list)
    recent_events: list[str] = Field(default_factory=list)
    active_narratives: list[str] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class CollaborationOutput(BaseModel):
    collaboration_id: str = Field(default_factory=lambda: f"COLLAB-{uuid4().hex[:6].upper()}")
    persona_ids: list[str]
    persona_names: list[str]
    task_type: str
    combined_insights: list[PersonaInsight]
    consensus_summary: str
    overall_confidence: float
    output_type: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class WarRoomActivationContext(BaseModel):
    war_room_type: str
    match_id: str = ""
    competition: str = ""
    opponent: str = ""
    urgency: str = "medium"
    context: dict[str, Any] = Field(default_factory=dict)
