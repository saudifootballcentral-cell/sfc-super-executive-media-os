"""Cross War Room Coordinator — Pydantic models."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class CoordinationMode(str, Enum):
    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"
    PRIORITY_BASED = "priority_based"


class ConflictType(str, Enum):
    RESOURCE_CONFLICT = "resource_conflict"
    PRIORITY_CONFLICT = "priority_conflict"
    DIVISION_CONFLICT = "division_conflict"
    EVENT_ROUTING_CONFLICT = "event_routing_conflict"


class CoordinationPlan(BaseModel):
    plan_id: str = Field(default_factory=lambda: str(uuid4()))
    active_war_room_ids: list[str] = Field(default_factory=list)
    mode: CoordinationMode
    division_assignments: dict[str, str] = Field(default_factory=dict)
    event_routing: dict[str, str] = Field(default_factory=dict)
    resource_split: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ConflictResolutionReport(BaseModel):
    report_id: str = Field(default_factory=lambda: str(uuid4()))
    conflict_type: ConflictType
    war_room_ids: list[str] = Field(default_factory=list)
    winner_id: str
    rationale: str
    resolved_at: datetime = Field(default_factory=datetime.utcnow)
