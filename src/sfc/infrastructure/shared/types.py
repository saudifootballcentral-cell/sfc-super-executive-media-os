"""Shared Pydantic models for all infrastructure services."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ComponentHealth(BaseModel):
    component: str
    status: HealthStatus
    last_check: datetime
    metrics: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)


class CostEntry(BaseModel):
    provider: str
    operation: str
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float
    timestamp: datetime
    run_id: str


class AuditEntry(BaseModel):
    entry_id: UUID = Field(default_factory=uuid4)
    component: str
    action: str
    actor: str = "system"
    run_id: str
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    success: bool = True


class MetricPoint(BaseModel):
    name: str
    value: float
    unit: str
    component: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    labels: dict[str, str] = Field(default_factory=dict)


class InfrastructureState(BaseModel):
    session_id: str
    started_at: datetime
    component_health: dict[str, ComponentHealth] = Field(default_factory=dict)
    total_cost_usd: float = 0.0
    total_calls: int = 0
    audit_log: list[AuditEntry] = Field(default_factory=list)
