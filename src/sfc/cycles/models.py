"""Operating cycle models — types and results for daily/weekly/monthly/quarterly/annual cycles."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class CycleType(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


class CyclePhase(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class CycleStep(BaseModel):
    """A single step within an operating cycle."""

    step_name: str
    status: CyclePhase = CyclePhase.PENDING
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: int = 0
    result: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class CycleResult(BaseModel):
    """Result of a completed operating cycle."""

    result_id: str = Field(default_factory=lambda: str(uuid4()))
    cycle_type: CycleType
    status: CyclePhase = CyclePhase.PENDING
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    duration_ms: int = 0
    steps: list[CycleStep] = Field(default_factory=list)
    executive_report: dict[str, Any] = Field(default_factory=dict)
    operational_reports: list[dict[str, Any]] = Field(default_factory=list)
    historical_analytics: dict[str, Any] = Field(default_factory=dict)
    cost_forecast: dict[str, Any] = Field(default_factory=dict)
    trigger_events: list[dict[str, Any]] = Field(default_factory=list)
    lessons_captured: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def to_summary(self) -> dict[str, Any]:
        return {
            "result_id": self.result_id,
            "cycle_type": self.cycle_type.value,
            "status": self.status.value,
            "duration_ms": self.duration_ms,
            "steps_completed": sum(1 for s in self.steps if s.status == CyclePhase.COMPLETED),
            "steps_total": len(self.steps),
            "errors": len(self.errors),
            "warnings": len(self.warnings),
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
