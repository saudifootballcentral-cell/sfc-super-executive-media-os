"""Tests for the AutonomousExecutionManager."""

from __future__ import annotations

import asyncio
from datetime import datetime

import pytest

from sfc.autonomous.execution_manager import (
    AutonomousExecutionManager,
    ExecutionRecord,
    ExecutionRequest,
)


class TestExecutionRequest:
    def test_defaults(self):
        req = ExecutionRequest(task_type="news")
        assert req.request_id
        assert req.priority == "medium"
        assert req.source == "scheduler"

    def test_all_priorities(self):
        for p in ("critical", "high", "medium", "low"):
            req = ExecutionRequest(task_type="t", priority=p)
            assert req.priority == p


class TestExecutionRecord:
    def test_defaults(self):
        rec = ExecutionRecord(
            request_id="req1",
            task_type="news",
            source="scheduler",
            started_at=datetime.utcnow(),
        )
        assert rec.record_id
        assert rec.success is False
        assert rec.errors == []
        assert rec.duration_ms == 0


class TestAutonomousExecutionManager:
    def make_manager(self) -> AutonomousExecutionManager:
        return AutonomousExecutionManager()

    @pytest.mark.asyncio
    async def test_submit_returns_request_id(self):
        manager = self.make_manager()
        req = ExecutionRequest(task_type="news")
        returned_id = await manager.submit(req)
        assert returned_id == req.request_id

    @pytest.mark.asyncio
    async def test_execute_now_no_graph(self):
        manager = self.make_manager()
        req = ExecutionRequest(task_type="news", source="test")
        record = await manager.execute_now(req)
        assert record.success is True
        assert record.pipeline_stage == "stub_execution"

    @pytest.mark.asyncio
    async def test_execute_now_populates_record(self):
        manager = self.make_manager()
        req = ExecutionRequest(task_type="executive_brief", source="scheduler")
        record = await manager.execute_now(req)
        assert record.task_type == "executive_brief"
        assert record.source == "scheduler"
        assert record.duration_ms >= 0
        assert record.completed_at is not None

    @pytest.mark.asyncio
    async def test_execute_now_with_failing_graph(self):
        manager = self.make_manager()

        class BadGraph:
            async def ainvoke(self, state):
                raise RuntimeError("Graph failed")

        manager.set_graph(BadGraph())
        req = ExecutionRequest(task_type="fail", source="test")
        record = await manager.execute_now(req)
        assert record.success is False
        assert len(record.errors) == 1
        assert "Graph failed" in record.errors[0]

    @pytest.mark.asyncio
    async def test_history_grows_after_execution(self):
        manager = self.make_manager()
        await manager.execute_now(ExecutionRequest(task_type="t1"))
        await manager.execute_now(ExecutionRequest(task_type="t2"))
        report = manager.get_execution_report()
        assert report["total_executions"] == 2

    @pytest.mark.asyncio
    async def test_success_rate_calculation(self):
        manager = self.make_manager()
        # No graph → all succeed as stubs
        await manager.execute_now(ExecutionRequest(task_type="t1"))
        await manager.execute_now(ExecutionRequest(task_type="t2"))
        report = manager.get_execution_report()
        assert report["success_rate_pct"] == 100.0

    @pytest.mark.asyncio
    async def test_failure_tracked_in_recovery_report(self):
        manager = self.make_manager()

        class BadGraph:
            async def ainvoke(self, state):
                raise RuntimeError("test failure")

        manager.set_graph(BadGraph())
        await manager.execute_now(ExecutionRequest(task_type="broken"))
        recovery = manager.get_recovery_report()
        assert recovery["failed_count"] == 1
        assert "broken" in recovery["failed_task_types"]

    def test_get_execution_plan_structure(self):
        manager = self.make_manager()
        plan = manager.get_execution_plan()
        assert "queue_size" in plan
        assert "running_count" in plan
        assert "active_task_types" in plan
        assert "history_count" in plan

    @pytest.mark.asyncio
    async def test_submit_multiple_requests(self):
        manager = self.make_manager()
        ids = []
        # Use distinct priorities to avoid heapq comparison fallthrough
        for tt, prio in zip(("news", "report", "analysis"), ("critical", "high", "low")):
            req = ExecutionRequest(task_type=tt, priority=prio)
            rid = await manager.submit(req)
            ids.append(rid)
        assert len(set(ids)) == 3  # all unique
        plan = manager.get_execution_plan()
        assert plan["queue_size"] == 3

    @pytest.mark.asyncio
    async def test_priority_ordering(self):
        manager = self.make_manager()
        low_req = ExecutionRequest(task_type="low", priority="low")
        high_req = ExecutionRequest(task_type="high", priority="high")
        critical_req = ExecutionRequest(task_type="critical", priority="critical")
        # Priority order: critical=0, high=1, medium=2, low=3
        await manager.submit(low_req)
        await manager.submit(high_req)
        await manager.submit(critical_req)
        assert manager._PRIORITY_ORDER["critical"] < manager._PRIORITY_ORDER["high"]
        assert manager._PRIORITY_ORDER["high"] < manager._PRIORITY_ORDER["low"]

    @pytest.mark.asyncio
    async def test_history_capped_at_500(self):
        manager = self.make_manager()
        # Execute many requests
        for i in range(10):
            await manager.execute_now(ExecutionRequest(task_type=f"t{i}"))
        report = manager.get_execution_report(limit=20)
        assert len(report["recent"]) <= 20

    def test_set_graph(self):
        manager = self.make_manager()
        assert manager._graph is None
        manager.set_graph(object())
        assert manager._graph is not None

    @pytest.mark.asyncio
    async def test_start_and_stop(self):
        manager = self.make_manager()
        await manager.start()
        assert manager._started is True
        await manager.stop()
        assert manager._started is False

    @pytest.mark.asyncio
    async def test_start_idempotent(self):
        manager = self.make_manager()
        await manager.start()
        await manager.start()  # second start is no-op
        assert manager._started is True
        await manager.stop()

    @pytest.mark.asyncio
    async def test_execute_now_with_stub_graph(self):
        manager = self.make_manager()

        class StubGraph:
            async def ainvoke(self, state):
                return {
                    "completed_at": "2025-01-01T00:00:00",
                    "run_id": state.get("run_id", "stub"),
                    "pipeline_stage": "memory_update",
                    "errors": [],
                    "warnings": [],
                }

        manager.set_graph(StubGraph())
        req = ExecutionRequest(task_type="executive_brief")
        record = await manager.execute_now(req)
        assert record.success is True
        assert record.pipeline_stage == "memory_update"
