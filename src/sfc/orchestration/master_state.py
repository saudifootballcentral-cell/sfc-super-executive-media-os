"""MasterState — envelope for a single orchestrated workflow run."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class WorkflowType(str, Enum):
    FULL_PIPELINE = "full_pipeline"
    SOCIAL_INTELLIGENCE_ONLY = "social_intelligence_only"
    CREATIVE_ONLY = "creative_only"
    PUBLISH_ONLY = "publish_only"
    DRY_RUN = "dry_run"
    REPORTING = "reporting"


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    PUBLISHING = "publishing"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"
    RECOVERED = "recovered"


class StageStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"


class ApprovalRecord(BaseModel):
    model_config = {"frozen": False}

    requested_at: datetime = Field(default_factory=datetime.utcnow)
    granted_at: datetime | None = None
    denied_at: datetime | None = None
    granted_by: str = ""
    denied_by: str = ""
    reason: str = ""
    governance_approved: bool = False
    operator_approved: bool = False

    @property
    def is_fully_approved(self) -> bool:
        return self.governance_approved and self.operator_approved


class StageRecord(BaseModel):
    model_config = {"frozen": False}

    stage_name: str
    status: StageStatus = StageStatus.PENDING
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: float = 0.0
    retry_count: int = 0
    error: str = ""
    artifacts: dict[str, Any] = Field(default_factory=dict)

    @property
    def duration_seconds(self) -> float:
        return self.duration_ms / 1000.0


class MasterState(BaseModel):
    """Top-level state envelope for a single orchestrated workflow run."""

    model_config = {"frozen": False}

    # Identity
    run_id: str = Field(default_factory=lambda: str(uuid4()))
    trigger_id: str = ""
    workflow_type: WorkflowType = WorkflowType.FULL_PIPELINE
    task_type: str = "content_pipeline"
    task_payload: dict[str, Any] = Field(default_factory=dict)

    # Initiator
    source: str = "api"
    initiator: str = "system"

    # Lifecycle
    status: RunStatus = RunStatus.PENDING
    current_stage: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None

    # Dry-run flag — publishing stage is skipped when True
    dry_run: bool = True

    # Per-stage tracking
    stages: dict[str, StageRecord] = Field(default_factory=dict)

    # Approval
    approval: ApprovalRecord = Field(default_factory=ApprovalRecord)

    # Accumulated output
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    artifacts: dict[str, Any] = Field(default_factory=dict)

    # Decisions log (governance, editorial, etc.)
    decisions: list[dict[str, Any]] = Field(default_factory=list)

    # Full execution history (audit)
    execution_history: list[dict[str, Any]] = Field(default_factory=list)

    # SFCState from each graph run (keyed by graph name)
    graph_states: dict[str, dict[str, Any]] = Field(default_factory=dict)

    def mark_stage_started(self, stage_name: str) -> None:
        self.stages[stage_name] = StageRecord(
            stage_name=stage_name,
            status=StageStatus.RUNNING,
            started_at=datetime.utcnow(),
        )
        self.current_stage = stage_name

    def mark_stage_completed(self, stage_name: str, artifacts: dict[str, Any] | None = None) -> None:
        rec = self.stages.get(stage_name)
        if rec:
            rec.status = StageStatus.COMPLETED
            rec.completed_at = datetime.utcnow()
            if rec.started_at:
                delta = rec.completed_at - rec.started_at
                rec.duration_ms = delta.total_seconds() * 1000
            if artifacts:
                rec.artifacts.update(artifacts)

    def mark_stage_failed(self, stage_name: str, error: str) -> None:
        rec = self.stages.get(stage_name)
        if rec:
            rec.status = StageStatus.FAILED
            rec.completed_at = datetime.utcnow()
            rec.error = error
        self.errors.append(f"[{stage_name}] {error}")

    def mark_stage_skipped(self, stage_name: str, reason: str = "") -> None:
        self.stages[stage_name] = StageRecord(
            stage_name=stage_name,
            status=StageStatus.SKIPPED,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            artifacts={"skip_reason": reason},
        )

    def add_decision(self, stage: str, decision: str, details: dict[str, Any] | None = None) -> None:
        self.decisions.append({
            "stage": stage,
            "decision": decision,
            "timestamp": datetime.utcnow().isoformat(),
            "details": details or {},
        })

    def append_history(self, event: str, details: dict[str, Any] | None = None) -> None:
        self.execution_history.append({
            "event": event,
            "timestamp": datetime.utcnow().isoformat(),
            "stage": self.current_stage,
            "details": details or {},
        })

    @property
    def total_duration_ms(self) -> float:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds() * 1000
        return 0.0

    @property
    def failed_stages(self) -> list[str]:
        return [name for name, rec in self.stages.items() if rec.status == StageStatus.FAILED]

    @property
    def completed_stages(self) -> list[str]:
        return [name for name, rec in self.stages.items() if rec.status == StageStatus.COMPLETED]

    def to_summary(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "workflow_type": self.workflow_type.value,
            "status": self.status.value,
            "dry_run": self.dry_run,
            "current_stage": self.current_stage,
            "completed_stages": self.completed_stages,
            "failed_stages": self.failed_stages,
            "total_duration_ms": self.total_duration_ms,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "approval": {
                "governance_approved": self.approval.governance_approved,
                "operator_approved": self.approval.operator_approved,
            },
        }
