from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field

from sfc.personas.shared.types import PersonaLifecycleState


class LifecycleTransition(BaseModel):
    transition_id: str = Field(default_factory=lambda: f"TRANS-{uuid4().hex[:6].upper()}")
    persona_id: str
    from_state: PersonaLifecycleState
    to_state: PersonaLifecycleState
    reason: str
    transitioned_at: datetime = Field(default_factory=datetime.utcnow)
    approved_by: str = "lifecycle_manager"


class VersionRecord(BaseModel):
    persona_id: str
    version: str
    changes: list[str]
    released_at: datetime = Field(default_factory=datetime.utcnow)


class MigrationPlan(BaseModel):
    plan_id: str = Field(default_factory=lambda: f"MIG-{uuid4().hex[:6].upper()}")
    from_persona_id: str
    to_persona_id: str
    steps: list[str]
    estimated_duration_hours: int = 2
    created_at: datetime = Field(default_factory=datetime.utcnow)


class LifecycleReport(BaseModel):
    report_id: str = Field(default_factory=lambda: f"LC-{uuid4().hex[:6].upper()}")
    period: str
    transitions: list[LifecycleTransition]
    active_count: int
    deprecated_count: int
    retired_count: int
    generated_at: datetime = Field(default_factory=datetime.utcnow)
