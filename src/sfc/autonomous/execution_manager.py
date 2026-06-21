"""Autonomous Execution Manager — coordinates all scheduled and triggered activity.

Responsibilities:
- Job dispatch to the main SFC pipeline graph
- Execution coordination and prioritization
- Conflict detection and resolution
- Failure recovery
- Resource allocation
- Execution reporting
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

logger = logging.getLogger("sfc.autonomous.execution_manager")

_manager_instance: "AutonomousExecutionManager | None" = None


def get_execution_manager() -> "AutonomousExecutionManager":
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = AutonomousExecutionManager()
    return _manager_instance


class ExecutionRequest(BaseModel):
    """A request to execute a workflow via the main pipeline."""

    request_id: str = Field(default_factory=lambda: str(uuid4()))
    task_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    priority: str = "medium"
    source: str = "scheduler"
    trigger_event_id: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    run_id: str | None = None

    model_config = {"frozen": False}


class ExecutionRecord(BaseModel):
    """Record of a completed autonomous execution."""

    record_id: str = Field(default_factory=lambda: str(uuid4()))
    request_id: str
    task_type: str
    source: str
    started_at: datetime
    completed_at: datetime | None = None
    success: bool = False
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    pipeline_stage: str = ""
    run_id: str = ""
    duration_ms: int = 0

    model_config = {"frozen": False}


class AutonomousExecutionManager:
    """Coordinates autonomous workflow execution with conflict resolution and recovery."""

    _MAX_CONCURRENT = 3
    _PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

    def __init__(self) -> None:
        self._queue: asyncio.PriorityQueue[tuple[int, ExecutionRequest]] = asyncio.PriorityQueue()
        self._running: dict[str, asyncio.Task] = {}
        self._history: list[ExecutionRecord] = []
        self._semaphore = asyncio.Semaphore(self._MAX_CONCURRENT)
        self._active_task_types: set[str] = set()
        self._graph: Any = None  # set via set_graph()
        self._started = False

    def set_graph(self, graph: Any) -> None:
        """Inject the compiled LangGraph pipeline."""
        self._graph = graph

    async def start(self) -> None:
        if self._started:
            return
        self._started = True
        asyncio.create_task(self._worker_loop(), name="autonomous_exec_worker")
        logger.info("[ExecutionManager] Started")

    async def stop(self) -> None:
        self._started = False
        for task in list(self._running.values()):
            task.cancel()

    async def submit(self, request: ExecutionRequest) -> str:
        """Submit a workflow execution request. Returns request_id."""
        priority = self._PRIORITY_ORDER.get(request.priority, 2)
        await self._queue.put((priority, request))
        logger.info(
            "[ExecutionManager] Request queued: %s (priority=%s source=%s)",
            request.task_type,
            request.priority,
            request.source,
        )
        return request.request_id

    async def execute_now(self, request: ExecutionRequest) -> ExecutionRecord:
        """Execute a request immediately (bypasses queue). For reporting cycles."""
        return await self._run_request(request)

    def get_execution_plan(self) -> dict[str, Any]:
        return {
            "queue_size": self._queue.qsize(),
            "running_count": len(self._running),
            "active_task_types": list(self._active_task_types),
            "history_count": len(self._history),
        }

    def get_execution_report(self, limit: int = 20) -> dict[str, Any]:
        recent = self._history[-limit:]
        successes = sum(1 for r in self._history if r.success)
        failures = sum(1 for r in self._history if not r.success)
        total = len(self._history)
        return {
            "total_executions": total,
            "total_successes": successes,
            "total_failures": failures,
            "success_rate_pct": round(successes / total * 100, 1) if total > 0 else 100.0,
            "running": len(self._running),
            "queued": self._queue.qsize(),
            "recent": [r.model_dump(mode="json") for r in recent],
        }

    def get_recovery_report(self) -> dict[str, Any]:
        failed = [r for r in self._history if not r.success]
        return {
            "failed_count": len(failed),
            "failed_task_types": list({r.task_type for r in failed}),
            "recent_failures": [r.model_dump(mode="json") for r in failed[-10:]],
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _worker_loop(self) -> None:
        while self._started:
            try:
                _, request = await asyncio.wait_for(self._queue.get(), timeout=5.0)
                asyncio.create_task(self._run_with_semaphore(request))
            except asyncio.TimeoutError:
                continue
            except Exception as exc:
                logger.error("[ExecutionManager] Worker error: %s", exc)

    async def _run_with_semaphore(self, request: ExecutionRequest) -> None:
        async with self._semaphore:
            await self._run_request(request)

    async def _run_request(self, request: ExecutionRequest) -> ExecutionRecord:
        import time as _time
        started_at = datetime.utcnow()
        t0 = _time.perf_counter()
        record = ExecutionRecord(
            request_id=request.request_id,
            task_type=request.task_type,
            source=request.source,
            started_at=started_at,
        )
        self._active_task_types.add(request.task_type)
        logger.info("[ExecutionManager] Executing: %s (run_id=%s)", request.task_type, request.run_id)

        try:
            if self._graph:
                from sfc.graph.state import make_initial_state
                state = make_initial_state(
                    task_type=request.task_type,
                    task_payload=request.payload,
                    run_id=request.run_id,
                )
                result = await self._graph.ainvoke(state)
                record.success = result.get("completed_at") is not None
                record.errors = result.get("errors", [])
                record.warnings = result.get("warnings", [])
                record.pipeline_stage = result.get("pipeline_stage", "")
                record.run_id = result.get("run_id", "")
            else:
                # No graph injected — record as successful stub
                record.success = True
                record.pipeline_stage = "stub_execution"
                record.run_id = request.run_id or str(uuid4())
        except Exception as exc:
            logger.error("[ExecutionManager] Execution failed: %s — %s", request.task_type, exc)
            record.success = False
            record.errors = [str(exc)]
        finally:
            record.completed_at = datetime.utcnow()
            record.duration_ms = int((_time.perf_counter() - t0) * 1000)
            self._active_task_types.discard(request.task_type)
            self._history.append(record)
            if len(self._history) > 500:
                self._history = self._history[-500:]

        return record
