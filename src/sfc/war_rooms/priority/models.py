"""Priority models for War Room conflict resolution."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class ConflictType(str, Enum):
    RESOURCE_CONFLICT = "resource_conflict"
    PRIORITY_CONFLICT = "priority_conflict"
    DIVISION_CONFLICT = "division_conflict"


class PriorityLevel(str, Enum):
    P0_EXECUTIVE = "p0_executive"
    P1_CRITICAL = "p1_critical"
    P2_HIGH = "p2_high"
    P3_MEDIUM = "p3_medium"
    P4_LOW = "p4_low"


class ConflictResolution(BaseModel):
    conflict_type: ConflictType
    winner_id: str
    loser_ids: list[str]
    rationale: str
    resolved_at: datetime = Field(default_factory=datetime.utcnow)


class PriorityDecision(BaseModel):
    decision_id: str = Field(default_factory=lambda: f"PRI-{uuid4().hex[:6].upper()}")
    winner_war_room_id: str
    loser_war_room_ids: list[str]
    conflict_type: ConflictType
    rationale: str
    decided_at: datetime = Field(default_factory=datetime.utcnow)
    executive_override: bool = False
