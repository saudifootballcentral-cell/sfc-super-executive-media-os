from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class PersonaCategory(str, Enum):
    JOURNALISM = "journalism"
    ANALYTICS = "analytics"
    CREATIVE = "creative"
    REVENUE = "revenue"
    GOVERNANCE = "governance"
    STRATEGY = "strategy"
    INTELLIGENCE = "intelligence"
    BROADCASTING = "broadcasting"
    SOCIAL_MEDIA = "social_media"
    SPECIALIST = "specialist"


class PersonaStatus(str, Enum):
    DRAFT = "draft"
    TESTING = "testing"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


class PersonaLifecycleState(str, Enum):
    DRAFT = "draft"
    TESTING = "testing"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


class PersonaProfile(BaseModel):
    persona_id: str = Field(default_factory=lambda: f"PERSONA-{uuid4().hex[:8].upper()}")
    name: str
    category: PersonaCategory
    description: str
    version: str = "1.0.0"
    owner: str = "system"
    status: PersonaStatus = PersonaStatus.DRAFT
    capabilities: list[str] = Field(default_factory=list)
    memory_profile: dict[str, Any] = Field(default_factory=dict)
    performance_score: float = 0.0
    health_score: float = 100.0
    activation_count: int = 0
    last_used: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PersonaMetrics(BaseModel):
    persona_id: str
    accuracy_score: float = 0.0
    relevance_score: float = 0.0
    quality_score: float = 0.0
    efficiency_score: float = 0.0
    engagement_impact: float = 0.0
    revenue_impact: float = 0.0
    usage_count: int = 0
    collaboration_score: float = 0.0
    avg_response_ms: float = 0.0
    measured_at: datetime = Field(default_factory=datetime.utcnow)


class PersonaHealth(BaseModel):
    persona_id: str
    status: str = "healthy"
    health_score: float = 100.0
    warnings: list[str] = Field(default_factory=list)
    last_checked: datetime = Field(default_factory=datetime.utcnow)


class PersonaAssignment(BaseModel):
    assignment_id: str = Field(default_factory=lambda: f"ASSIGN-{uuid4().hex[:6].upper()}")
    persona_id: str
    task_type: str
    run_id: str = ""
    assigned_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    output_summary: str = ""


class PersonaActivation(BaseModel):
    activation_id: str = Field(default_factory=lambda: f"ACT-{uuid4().hex[:6].upper()}")
    persona_id: str
    trigger: str
    activated_at: datetime = Field(default_factory=datetime.utcnow)
    deactivated_at: datetime | None = None
    active: bool = True
    context: dict[str, Any] = Field(default_factory=dict)


class PersonaMemoryState(BaseModel):
    persona_id: str
    knowledge_snapshot: dict[str, Any] = Field(default_factory=dict)
    learning_records: list[dict[str, Any]] = Field(default_factory=list)
    context_package: dict[str, Any] = Field(default_factory=dict)
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class PersonaGovernanceState(BaseModel):
    persona_id: str
    approved: bool = False
    risk_score: float = 0.0
    compliance_notes: list[str] = Field(default_factory=list)
    last_reviewed: datetime | None = None
    reviewer: str = "governance_framework"


class PersonaAnalyticsState(BaseModel):
    persona_id: str
    period: str = "session"
    total_activations: int = 0
    avg_performance_score: float = 0.0
    top_tasks: list[str] = Field(default_factory=list)
    improvement_areas: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
