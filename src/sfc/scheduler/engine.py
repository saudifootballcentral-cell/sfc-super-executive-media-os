"""SFC Scheduler Engine — asyncio-native job scheduler.

Runs as a background service. Supports cron, interval, one-time,
event-based, war-room-based, persona-based, and cost-based triggers.

Usage:
    scheduler = get_scheduler()
    scheduler.add_job(make_daily_brief_job())
    await scheduler.start()   # non-blocking; runs _tick() as background task
    ...
    await scheduler.stop()
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime
from typing import Any, Callable, Awaitable

from sfc.scheduler.calendar import CronExpression
from sfc.scheduler.jobs import (
    JobDefinition,
    JobPriority,
    JobRecord,
    JobStatus,
    JobType,
)
from sfc.scheduler.persistence import SchedulerPersistence
from sfc.scheduler.state import SchedulerState
from sfc.scheduler.triggers import TriggerConfig

logger = logging.getLogger("sfc.scheduler.engine")

_TICK_INTERVAL_SECONDS = 30
_MAX_CONCURRENT_JOBS = 10

# Global singleton
_scheduler_instance: "SFCScheduler | None" = None


def get_scheduler() -> "SFCScheduler":
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = SFCScheduler()
    return _scheduler_instance


JobHandler = Callable[[JobDefinition], Awaitable[dict[str, Any]]]


class SFCScheduler:
    """Async-native scheduler with cron, interval, one-time and event-based jobs."""

    def __init__(
        self,
        persistence: SchedulerPersistence | None = None,
        tick_interval: int = _TICK_INTERVAL_SECONDS,
    ) -> None:
        self._state = SchedulerState()
        self._persistence = persistence or SchedulerPersistence()
        self._tick_interval = tick_interval
        self._running_tasks: dict[str, asyncio.Task] = {}
        self._triggers: list[TriggerConfig] = []
        self._ticker_task: asyncio.Task | None = None
        self._handlers: dict[str, JobHandler] = {}
        self._semaphore: asyncio.Semaphore | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        if self._state.started_at is not None:
            logger.warning("[Scheduler] Already running — ignoring start()")
            return
        self._semaphore = asyncio.Semaphore(_MAX_CONCURRENT_JOBS)
        self._state.started_at = datetime.utcnow()
        self._ticker_task = asyncio.create_task(self._ticker_loop(), name="sfc_scheduler_ticker")
        logger.info("[Scheduler] Started — tick_interval=%ds", self._tick_interval)

    async def stop(self) -> None:
        if self._ticker_task:
            self._ticker_task.cancel()
            try:
                await self._ticker_task
            except asyncio.CancelledError:
                pass
        for task in list(self._running_tasks.values()):
            task.cancel()
        self._state.started_at = None
        logger.info("[Scheduler] Stopped")

    # ------------------------------------------------------------------
    # Job management
    # ------------------------------------------------------------------

    def add_job(self, job: JobDefinition) -> str:
        job = job.model_copy(deep=True)
        job.next_run_at = self._compute_next_run(job)
        self._state.add_job(job)
        self._persistence.save_job(job)
        logger.info("[Scheduler] Job added: %s (%s)", job.name, job.job_id)
        return job.job_id

    def remove_job(self, job_id: str) -> bool:
        removed = self._state.remove_job(job_id)
        if removed:
            self._persistence.delete_job(job_id)
            if job_id in self._running_tasks:
                self._running_tasks[job_id].cancel()
                del self._running_tasks[job_id]
        return removed

    def pause_job(self, job_id: str) -> bool:
        job = self._state.get_job(job_id)
        if job is None:
            return False
        job.status = JobStatus.PAUSED
        job.enabled = False
        return True

    def resume_job(self, job_id: str) -> bool:
        job = self._state.get_job(job_id)
        if job is None:
            return False
        job.status = JobStatus.PENDING
        job.enabled = True
        job.next_run_at = self._compute_next_run(job)
        return True

    def list_jobs(self) -> list[JobDefinition]:
        return list(self._state.jobs.values())

    def get_job(self, job_id: str) -> JobDefinition | None:
        return self._state.get_job(job_id)

    # ------------------------------------------------------------------
    # Trigger management
    # ------------------------------------------------------------------

    def add_trigger(self, trigger: TriggerConfig) -> str:
        self._triggers.append(trigger)
        logger.info("[Scheduler] Trigger added: %s", trigger.name)
        return trigger.trigger_id

    def register_handler(self, task_type: str, handler: JobHandler) -> None:
        """Register an async callable to handle jobs of a given task_type."""
        self._handlers[task_type] = handler

    # ------------------------------------------------------------------
    # Autonomous trigger evaluation
    # ------------------------------------------------------------------

    async def evaluate_triggers(self, context: dict[str, Any]) -> list[str]:
        """Evaluate all registered triggers against context. Returns fired job IDs."""
        fired: list[str] = []
        for trigger in self._triggers:
            if trigger.should_fire(context):
                job = JobDefinition(
                    name=f"auto_{trigger.trigger_type.value}",
                    job_type=JobType.EVENT_BASED,
                    task_type=trigger.job_task_type,
                    payload={**trigger.job_payload, "trigger_type": trigger.trigger_type.value},
                    priority=JobPriority.HIGH,
                )
                job_id = self.add_job(job)
                trigger.last_fired_at = datetime.utcnow()
                logger.info("[Scheduler] Trigger fired: %s → job=%s", trigger.name, job_id)
                asyncio.create_task(self._execute_job_by_id(job_id))
                fired.append(job_id)
        return fired

    # ------------------------------------------------------------------
    # Missed job recovery
    # ------------------------------------------------------------------

    def recover_missed_jobs(self) -> list[str]:
        """Mark jobs whose scheduled time has passed as MISSED and reschedule."""
        now = datetime.utcnow()
        missed: list[str] = []
        for job in self._state.jobs.values():
            if (
                job.enabled
                and job.next_run_at
                and job.next_run_at < now
                and job.status not in (JobStatus.RUNNING, JobStatus.PAUSED)
                and job.job_type not in (JobType.ONE_TIME, JobType.EVENT_BASED)
            ):
                logger.warning("[Scheduler] Missed job detected: %s", job.name)
                job.status = JobStatus.MISSED
                job.failure_count += 1
                missed.append(job.job_id)
                job.next_run_at = self._compute_next_run(job)
        return missed

    # ------------------------------------------------------------------
    # Health and reporting
    # ------------------------------------------------------------------

    def get_health(self) -> dict[str, Any]:
        return self._state.get_health().model_dump()

    def get_execution_report(self) -> dict[str, Any]:
        return {
            "scheduler": self._state.to_summary(),
            "jobs": [
                {
                    "job_id": j.job_id,
                    "name": j.name,
                    "status": j.status.value,
                    "run_count": j.run_count,
                    "failure_count": j.failure_count,
                    "last_run_at": j.last_run_at.isoformat() if j.last_run_at else None,
                    "next_run_at": j.next_run_at.isoformat() if j.next_run_at else None,
                }
                for j in self._state.jobs.values()
            ],
            "recent_history": [
                r.model_dump(mode="json") for r in self._state.job_history[-20:]
            ],
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _ticker_loop(self) -> None:
        while True:
            try:
                self._state.last_tick_at = datetime.utcnow()
                self._state.tick_count += 1
                await self._check_due_jobs()
                await asyncio.sleep(self._tick_interval)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("[Scheduler] Ticker error: %s", exc)
                await asyncio.sleep(self._tick_interval)

    async def _check_due_jobs(self) -> None:
        now = datetime.utcnow()
        for job in list(self._state.jobs.values()):
            if not job.enabled or job.status == JobStatus.PAUSED:
                continue
            if job.job_id in self._running_tasks:
                continue
            if self._is_due(job, now):
                asyncio.create_task(self._execute_job_by_id(job.job_id))

    def _is_due(self, job: JobDefinition, now: datetime) -> bool:
        if job.job_type == JobType.EVENT_BASED:
            return False
        if job.next_run_at and now >= job.next_run_at:
            return True
        return False

    async def _execute_job_by_id(self, job_id: str) -> None:
        job = self._state.get_job(job_id)
        if job is None:
            return
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(_MAX_CONCURRENT_JOBS)
        async with self._semaphore:
            await self._execute_job(job)

    async def _execute_job(self, job: JobDefinition) -> JobRecord:
        start = time.perf_counter()
        started_at = datetime.utcnow()
        record = JobRecord(
            job_id=job.job_id,
            job_name=job.name,
            task_type=job.task_type,
            started_at=started_at,
        )
        job.status = JobStatus.RUNNING
        job.last_run_at = started_at
        job.run_count += 1
        self._state.running_job_ids.add(job.job_id)

        try:
            result = await self._dispatch(job)
            record.status = JobStatus.COMPLETED
            record.result_summary = result if isinstance(result, dict) else {}
            job.status = JobStatus.COMPLETED
            job.last_error = None
            self._state.total_successes += 1
            logger.info("[Scheduler] Job completed: %s", job.name)
        except Exception as exc:
            error_msg = str(exc)
            logger.error("[Scheduler] Job failed: %s — %s", job.name, error_msg)
            record.status = JobStatus.FAILED
            record.error = error_msg
            job.status = JobStatus.FAILED
            job.last_error = error_msg
            job.failure_count += 1
            self._state.total_failures += 1
            if job.failure_count < job.max_retries:
                job.status = JobStatus.RETRYING
                await asyncio.sleep(min(job.retry_delay_seconds, 10))
        finally:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            record.completed_at = datetime.utcnow()
            record.duration_ms = elapsed_ms
            self._state.running_job_ids.discard(job.job_id)
            self._state.total_executions += 1
            self._state.add_record(record)
            self._persistence.save_record(record)
            job.next_run_at = self._compute_next_run(job)

        return record

    async def _dispatch(self, job: JobDefinition) -> dict[str, Any]:
        """Dispatch a job to its registered handler or a default noop."""
        handler = self._handlers.get(job.task_type)
        if handler:
            return await asyncio.wait_for(
                handler(job), timeout=float(job.timeout_seconds)
            )
        logger.debug("[Scheduler] No handler for task_type=%s — returning stub", job.task_type)
        return {"dispatched": True, "task_type": job.task_type, "stub": True}

    def _compute_next_run(self, job: JobDefinition) -> datetime | None:
        now = datetime.utcnow()
        if not job.enabled:
            return None
        if job.job_type == JobType.ONE_TIME:
            return job.run_at if job.run_at and job.run_at > now else None
        if job.job_type == JobType.INTERVAL and job.interval_seconds:
            return datetime.utcnow().replace(microsecond=0)
        if job.job_type == JobType.CRON and job.cron_expression:
            try:
                return CronExpression(job.cron_expression).next_run(now)
            except Exception:
                return None
        return None
