from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class CollaborationRole(str, Enum):
    LEAD = "lead"
    CONTRIBUTOR = "contributor"
    REVIEWER = "reviewer"
    SPECIALIST = "specialist"


class PersonaTeam(BaseModel):
    team_id: str = Field(default_factory=lambda: f"TEAM-{uuid4().hex[:6].upper()}")
    task_type: str
    members: list[dict]
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CollaborationPlan(BaseModel):
    plan_id: str = Field(default_factory=lambda: f"COLLAB-{uuid4().hex[:6].upper()}")
    team: PersonaTeam
    workflow_steps: list[dict]
    expected_outputs: list[str]
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ConsensusReport(BaseModel):
    report_id: str = Field(default_factory=lambda: f"CONS-{uuid4().hex[:6].upper()}")
    plan_id: str
    contributions: dict[str, str]
    consensus_output: str
    confidence: float
    generated_at: datetime = Field(default_factory=datetime.utcnow)
