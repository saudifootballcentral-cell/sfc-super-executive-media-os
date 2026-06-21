"""Scheduler state — runtime snapshot of all jobs, history and health."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from sfc.scheduler.jobs import JobDefinition, JobRecord, JobStatus


class SchedulerHealth(BaseModel):
    """Snapshot of scheduler health metrics."""

    is_running: bool = False
    total_jobs: int = 0
    enabled_jobs: int = 0
    running_jobs: int = 0
    paused_jobs: int = 0
    failed_jobs_last_hour: int = 0
    completed_jobs_last_hour: int = 0
    missed_jobs: int = 0
    success_rate_pct: float = 100.0
    avg_execution_ms: float = 0.0
    last_tick_at: datetime | None = None
    uptime_seconds: float = 0.0


class SchedulerState(BaseModel):
    """Complete runtime state of the SFC Scheduler."""

    started_at: datetime | None = None
    last_tick_at: datetime | None = None
    tick_count: int = 0
    jobs: dict[str, JobDefinition] = Field(default_factory=dict)
    running_job_ids: set[str] = Field(default_factory=set)
    job_history: list[JobRecord] = Field(default_factory=list)
    total_executions: int = 0
    total_failures: int = 0
    total_successes: int = 0

    model_config = {"frozen": False, "arbitrary_types_allowed": True}

    def add_job(self, job: JobDefinition) -> None:
        self.jobs[job.job_id] = job

    def remove_job(self, job_id: str) -> bool:
        return bool(self.jobs.pop(job_id, None))

    def get_job(self, job_id: str) -> JobDefinition | None:
        return self.jobs.get(job_id)

    def add_record(self, record: JobRecord) -> None:
        self.job_history.append(record)
        # Keep last 1000 records
        if len(self.job_history) > 1000:
            self.job_history = self.job_history[-1000:]

    def get_health(self) -> SchedulerHealth:
        now = datetime.utcnow()
        cutoff = now.timestamp() - 3600
        recent = [
            r for r in self.job_history
            if r.started_at and r.started_at.timestamp() >= cutoff
        ]
        failed_recent = [r for r in recent if r.status == JobStatus.FAILED]
        completed_recent = [r for r in recent if r.status == JobStatus.COMPLETED]
        durations = [r.duration_ms for r in recent if r.duration_ms > 0]
        total_recent = len(recent)
        missed = sum(1 for j in self.jobs.values() if j.status == JobStatus.MISSED)
        success_rate = (
            (len(completed_recent) / total_recent * 100) if total_recent > 0 else 100.0
        )
        return SchedulerHealth(
            is_running=bool(self.started_at),
            total_jobs=len(self.jobs),
            enabled_jobs=sum(1 for j in self.jobs.values() if j.enabled),
            running_jobs=len(self.running_job_ids),
            paused_jobs=sum(1 for j in self.jobs.values() if j.status == JobStatus.PAUSED),
            failed_jobs_last_hour=len(failed_recent),
            completed_jobs_last_hour=len(completed_recent),
            missed_jobs=missed,
            success_rate_pct=round(success_rate, 1),
            avg_execution_ms=round(sum(durations) / len(durations), 1) if durations else 0.0,
            last_tick_at=self.last_tick_at,
            uptime_seconds=(now - self.started_at).total_seconds() if self.started_at else 0.0,
        )

    def to_summary(self) -> dict[str, Any]:
        health = self.get_health()
        return {
            "is_running": health.is_running,
            "total_jobs": health.total_jobs,
            "enabled_jobs": health.enabled_jobs,
            "running_jobs": health.running_jobs,
            "success_rate_pct": health.success_rate_pct,
            "total_executions": self.total_executions,
            "total_failures": self.total_failures,
            "uptime_seconds": health.uptime_seconds,
            "last_tick_at": self.last_tick_at.isoformat() if self.last_tick_at else None,
        }
