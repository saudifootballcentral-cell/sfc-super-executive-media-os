"""Scheduler job definitions — types, status, records, and definitions."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class JobType(str, Enum):
    CRON = "cron"
    INTERVAL = "interval"
    ONE_TIME = "one_time"
    EVENT_BASED = "event_based"
    WAR_ROOM = "war_room"
    PERSONA = "persona"
    AI_COST = "ai_cost"


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    MISSED = "missed"
    RETRYING = "retrying"


class JobPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class JobDefinition(BaseModel):
    """A scheduled job definition."""

    job_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: str = ""
    job_type: JobType
    task_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    priority: JobPriority = JobPriority.MEDIUM

    # Scheduling parameters
    interval_seconds: int | None = None
    cron_expression: str | None = None
    run_at: datetime | None = None
    event_trigger: str | None = None
    war_room_type: str | None = None
    persona_id: str | None = None
    cost_threshold_usd: float | None = None

    # Execution controls
    max_retries: int = 3
    retry_delay_seconds: int = 60
    timeout_seconds: int = 300
    enabled: bool = True

    # Runtime state (updated by engine)
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_run_at: datetime | None = None
    next_run_at: datetime | None = None
    run_count: int = 0
    failure_count: int = 0
    last_error: str | None = None

    model_config = {"frozen": False}


class JobRecord(BaseModel):
    """Execution record for a completed job run."""

    record_id: str = Field(default_factory=lambda: str(uuid4()))
    job_id: str
    job_name: str
    task_type: str
    started_at: datetime
    completed_at: datetime | None = None
    status: JobStatus = JobStatus.PENDING
    duration_ms: int = 0
    error: str | None = None
    result_summary: dict[str, Any] = Field(default_factory=dict)
    retry_count: int = 0

    model_config = {"frozen": False}


# Pre-built job factory helpers
def make_daily_brief_job() -> JobDefinition:
    return JobDefinition(
        name="daily_executive_brief",
        description="Generate daily executive brief at 7:00 AM",
        job_type=JobType.CRON,
        task_type="executive_brief",
        cron_expression="0 7 * * *",
        priority=JobPriority.HIGH,
        payload={"report_type": "daily", "include_ai_metrics": True},
    )


def make_trend_scan_job(interval_minutes: int = 30) -> JobDefinition:
    return JobDefinition(
        name="trend_scan",
        description=f"Scan for trends every {interval_minutes} minutes",
        job_type=JobType.INTERVAL,
        task_type="trend_scan",
        interval_seconds=interval_minutes * 60,
        priority=JobPriority.MEDIUM,
        payload={"scan_depth": "standard"},
    )


def make_weekly_report_job() -> JobDefinition:
    return JobDefinition(
        name="weekly_performance_report",
        description="Generate weekly performance report every Monday at 9:00 AM",
        job_type=JobType.CRON,
        task_type="weekly_report",
        cron_expression="0 9 * * 1",
        priority=JobPriority.HIGH,
        payload={"report_type": "weekly"},
    )


def make_cost_guard_job(threshold_usd: float = 50.0) -> JobDefinition:
    return JobDefinition(
        name="ai_cost_guard",
        description="Alert when daily AI cost exceeds threshold",
        job_type=JobType.AI_COST,
        task_type="cost_alert",
        cost_threshold_usd=threshold_usd,
        priority=JobPriority.HIGH,
        payload={"threshold_usd": threshold_usd},
    )
