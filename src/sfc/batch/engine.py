"""Batch Processing Engine — concurrent multi-task graph execution.

Supports batch intelligence scans, content creation, persona analysis,
reporting, publishing, and simulations with concurrency controls,
rate limits, retry policies, and execution metrics.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime
from typing import Any, Callable, Awaitable
from uuid import uuid4

from pydantic import BaseModel, Field

logger = logging.getLogger("sfc.batch.engine")

_DEFAULT_CONCURRENCY = 3
_DEFAULT_RATE_LIMIT_PER_MINUTE = 20
_DEFAULT_MAX_RETRIES = 2


class BatchJob(BaseModel):
    """A single item within a batch."""

    job_id: str = Field(default_factory=lambda: str(uuid4()))
    task_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    priority: int = 5  # 1=highest, 10=lowest
    run_id: str | None = None

    model_config = {"frozen": False}


class BatchResult(BaseModel):
    """Result of a single batch job execution."""

    job_id: str
    task_type: str
    success: bool
    result: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    duration_ms: int = 0
    retry_count: int = 0
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None

    model_config = {"frozen": False}


class BatchSummary(BaseModel):
    """Aggregate summary of a batch run."""

    batch_id: str = Field(default_factory=lambda: str(uuid4()))
    batch_name: str = ""
    total: int
    successful: int
    failed: int
    skipped: int = 0
    success_rate_pct: float
    total_duration_ms: int
    avg_duration_ms: float
    started_at: datetime
    completed_at: datetime
    errors: list[str] = Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


BatchHandler = Callable[[BatchJob], Awaitable[dict[str, Any]]]


class BatchEngine:
    """Concurrent batch processor with rate limiting and retry policies."""

    def __init__(
        self,
        concurrency: int = _DEFAULT_CONCURRENCY,
        rate_limit_per_minute: int = _DEFAULT_RATE_LIMIT_PER_MINUTE,
        max_retries: int = _DEFAULT_MAX_RETRIES,
    ) -> None:
        self._concurrency = concurrency
        self._rate_limit = rate_limit_per_minute
        self._max_retries = max_retries
        self._semaphore: asyncio.Semaphore | None = None
        self._handlers: dict[str, BatchHandler] = {}
        self._summaries: list[BatchSummary] = []
        self._rate_tokens: float = float(rate_limit_per_minute)
        self._last_refill: float = time.monotonic()

    def register_handler(self, task_type: str, handler: BatchHandler) -> None:
        self._handlers[task_type] = handler

    async def run(
        self,
        jobs: list[BatchJob],
        batch_name: str = "",
        timeout_per_job: float = 120.0,
    ) -> BatchSummary:
        """Execute a batch of jobs concurrently. Returns aggregate summary."""
        if not self._semaphore:
            self._semaphore = asyncio.Semaphore(self._concurrency)

        started_at = datetime.utcnow()
        t0 = time.perf_counter()
        jobs_sorted = sorted(jobs, key=lambda j: j.priority)

        tasks = [
            asyncio.create_task(self._run_job(job, timeout_per_job))
            for job in jobs_sorted
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        batch_results: list[BatchResult] = []
        errors: list[str] = []
        for r in results:
            if isinstance(r, BatchResult):
                batch_results.append(r)
                if not r.success and r.error:
                    errors.append(f"[{r.job_id}] {r.error}")
            elif isinstance(r, Exception):
                errors.append(str(r))

        successful = sum(1 for r in batch_results if r.success)
        failed = sum(1 for r in batch_results if not r.success)
        total_ms = int((time.perf_counter() - t0) * 1000)
        durations = [r.duration_ms for r in batch_results]
        avg_ms = sum(durations) / len(durations) if durations else 0.0

        summary = BatchSummary(
            batch_name=batch_name,
            total=len(jobs),
            successful=successful,
            failed=failed,
            success_rate_pct=round(successful / len(jobs) * 100, 1) if jobs else 100.0,
            total_duration_ms=total_ms,
            avg_duration_ms=round(avg_ms, 1),
            started_at=started_at,
            completed_at=datetime.utcnow(),
            errors=errors[:20],
        )
        self._summaries.append(summary)
        logger.info(
            "[BatchEngine] %s complete: %d/%d succeeded in %dms",
            batch_name or "batch",
            successful,
            len(jobs),
            total_ms,
        )
        return summary

    async def run_intelligence_scan(
        self, topics: list[str], graph: Any | None = None
    ) -> BatchSummary:
        """Batch intelligence scan across multiple topics."""
        jobs = [
            BatchJob(task_type="news", payload={"topic": t, "batch_scan": True})
            for t in topics
        ]
        if graph:
            self.register_handler("news", self._make_graph_handler(graph))
        return await self.run(jobs, batch_name="intelligence_scan")

    async def run_content_batch(
        self, items: list[dict[str, Any]], graph: Any | None = None
    ) -> BatchSummary:
        """Batch content creation."""
        jobs = [
            BatchJob(task_type=item.get("task_type", "news"), payload=item)
            for item in items
        ]
        if graph:
            self.register_handler("news", self._make_graph_handler(graph))
        return await self.run(jobs, batch_name="content_batch")

    async def run_persona_analysis(
        self, contexts: list[dict[str, Any]]
    ) -> BatchSummary:
        """Batch persona analysis."""
        jobs = [
            BatchJob(task_type="persona_analysis", payload=ctx)
            for ctx in contexts
        ]
        return await self.run(jobs, batch_name="persona_analysis")

    async def run_batch_reporting(
        self, states: list[dict[str, Any]]
    ) -> BatchSummary:
        """Batch report generation."""
        jobs = [
            BatchJob(task_type="reporting", payload=s)
            for s in states
        ]
        return await self.run(jobs, batch_name="batch_reporting")

    def get_summaries(self, limit: int = 20) -> list[dict[str, Any]]:
        return [s.to_dict() for s in self._summaries[-limit:]]

    def get_metrics(self) -> dict[str, Any]:
        if not self._summaries:
            return {"total_batches": 0}
        total_jobs = sum(s.total for s in self._summaries)
        total_ok = sum(s.successful for s in self._summaries)
        return {
            "total_batches": len(self._summaries),
            "total_jobs": total_jobs,
            "total_successful": total_ok,
            "overall_success_rate_pct": round(total_ok / total_jobs * 100, 1) if total_jobs > 0 else 100.0,
            "avg_batch_duration_ms": round(
                sum(s.total_duration_ms for s in self._summaries) / len(self._summaries), 1
            ),
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _run_job(self, job: BatchJob, timeout: float) -> BatchResult:
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self._concurrency)
        async with self._semaphore:
            await self._rate_limit_wait()
            return await self._execute_with_retry(job, timeout)

    async def _execute_with_retry(self, job: BatchJob, timeout: float) -> BatchResult:
        t0 = time.perf_counter()
        retry = 0
        last_error = ""
        while retry <= self._max_retries:
            try:
                result = await asyncio.wait_for(
                    self._dispatch(job), timeout=timeout
                )
                return BatchResult(
                    job_id=job.job_id,
                    task_type=job.task_type,
                    success=True,
                    result=result,
                    duration_ms=int((time.perf_counter() - t0) * 1000),
                    retry_count=retry,
                    completed_at=datetime.utcnow(),
                )
            except (asyncio.TimeoutError, Exception) as exc:
                last_error = str(exc)
                retry += 1
                if retry <= self._max_retries:
                    await asyncio.sleep(2 ** retry)
        return BatchResult(
            job_id=job.job_id,
            task_type=job.task_type,
            success=False,
            error=last_error,
            duration_ms=int((time.perf_counter() - t0) * 1000),
            retry_count=retry - 1,
            completed_at=datetime.utcnow(),
        )

    async def _dispatch(self, job: BatchJob) -> dict[str, Any]:
        handler = self._handlers.get(job.task_type)
        if handler:
            return await handler(job)
        return {"stub": True, "task_type": job.task_type, "job_id": job.job_id}

    async def _rate_limit_wait(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._rate_tokens = min(
            float(self._rate_limit),
            self._rate_tokens + elapsed * (self._rate_limit / 60.0),
        )
        self._last_refill = now
        if self._rate_tokens < 1.0:
            wait = (1.0 - self._rate_tokens) * (60.0 / self._rate_limit)
            await asyncio.sleep(wait)
            self._rate_tokens = 0.0
        else:
            self._rate_tokens -= 1.0

    def _make_graph_handler(self, graph: Any) -> BatchHandler:
        async def _handler(job: BatchJob) -> dict[str, Any]:
            from sfc.graph.state import make_initial_state
            state = make_initial_state(
                task_type=job.task_type,
                task_payload=job.payload,
                run_id=job.run_id,
            )
            result = await graph.ainvoke(state)
            return {
                "run_id": result.get("run_id", ""),
                "pipeline_stage": result.get("pipeline_stage", ""),
                "content_published": len(result.get("approved_content", [])),
                "errors": result.get("errors", []),
            }
        return _handler
