"""Live Operations Command — Pydantic models."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class OperationalStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    OFFLINE = "offline"


class WorkflowStatus(BaseModel):
    workflow_id: str
    name: str
    status: OperationalStatus
    progress_pct: float = 0.0
    started_at: datetime = Field(default_factory=datetime.utcnow)
    last_update: datetime = Field(default_factory=datetime.utcnow)
    errors: list[str] = Field(default_factory=list)


class OperationsSnapshot(BaseModel):
    snapshot_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    active_workflows: list[WorkflowStatus] = Field(default_factory=list)
    war_rooms_active: int = 0
    agents_healthy: int = 0
    agents_total: int = 0
    platforms_healthy: int = 0
    publishing_queue_depth: int = 0
    overall_status: OperationalStatus = OperationalStatus.HEALTHY


class OperationsAlert(BaseModel):
    alert_id: str = Field(default_factory=lambda: str(uuid4()))
    severity: str = "medium"
    message: str
    source: str = "operations"
    raised_at: datetime = Field(default_factory=datetime.utcnow)
    resolved: bool = False
