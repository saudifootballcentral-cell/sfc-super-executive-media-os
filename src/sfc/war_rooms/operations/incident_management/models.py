"""Incident Management Engine — Pydantic models."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class IncidentType(str, Enum):
    PLATFORM_FAILURE = "platform_failure"
    PUBLISHING_FAILURE = "publishing_failure"
    AGENT_FAILURE = "agent_failure"
    TOOL_FAILURE = "tool_failure"
    DATA_FAILURE = "data_failure"
    SECURITY_INCIDENT = "security_incident"
    GOVERNANCE_FAILURE = "governance_failure"


class IncidentSeverity(str, Enum):
    P1 = "p1"
    P2 = "p2"
    P3 = "p3"
    P4 = "p4"


class IncidentStatus(str, Enum):
    DETECTED = "detected"
    CONTAINED = "contained"
    RECOVERING = "recovering"
    RESOLVED = "resolved"
    POSTMORTEM = "postmortem"


class Incident(BaseModel):
    incident_id: str = Field(default_factory=lambda: f"INC-{uuid4().hex[:8].upper()}")
    incident_type: IncidentType
    severity: IncidentSeverity
    status: IncidentStatus = IncidentStatus.DETECTED
    title: str
    description: str
    impact: str
    affected_components: list[str] = Field(default_factory=list)
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    contained_at: datetime | None = None
    resolved_at: datetime | None = None
    root_cause: str = ""
    timeline: list[dict[str, Any]] = Field(default_factory=list)


class RecoveryPlan(BaseModel):
    incident_id: str
    steps: list[str] = Field(default_factory=list)
    estimated_recovery_minutes: int = 30
    owner: str = "ops_team"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Postmortem(BaseModel):
    incident_id: str
    title: str
    summary: str
    timeline: list[dict[str, Any]] = Field(default_factory=list)
    root_cause: str
    contributing_factors: list[str] = Field(default_factory=list)
    impact_assessment: str
    lessons_learned: list[str] = Field(default_factory=list)
    action_items: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
