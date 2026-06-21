"""Tests for the Batch Processing Engine."""

from __future__ import annotations

import asyncio
from datetime import datetime

import pytest

from sfc.batch.engine import BatchEngine, BatchJob, BatchResult, BatchSummary


class TestBatchJob:
    def test_defaults(self):
        job = BatchJob(task_type="news")
        assert job.job_id
        assert job.priority == 5
        assert job.payload == {}

    def test_with_payload(self):
        job = BatchJob(task_type="report", payload={"topic": "football"}, priority=1)
        assert job.payload["topic"] == "football"
        assert job.priority == 1


class TestBatchResult:
    def test_success(self):
        r = BatchResult(job_id="j1", task_type="news", success=True)
        assert r.success is True
        assert r.error is None

    def test_failure(self):
        r = BatchResult(job_id="j1", task_type="news", success=False, error="timeout")
        assert r.success is False
        assert r.error == "timeout"


class TestBatchSummary:
    def test_to_dict(self):
        s = BatchSummary(
            total=5,
            successful=4,
            failed=1,
            success_rate_pct=80.0,
            total_duration_ms=500,
            avg_duration_ms=100.0,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )
        d = s.to_dict()
        assert d["total"] == 5
        assert d["successful"] == 4


class TestBatchEngine:
    def make_engine(self) -> BatchEngine:
        return BatchEngine(concurrency=2, rate_limit_per_minute=60, max_retries=0)

    @pytest.mark.asyncio
    async def test_empty_batch_returns_summary(self):
        engine = self.make_engine()
        summary = await engine.run([])
        assert summary.total == 0
        assert summary.success_rate_pct == 100.0

    @pytest.mark.asyncio
    async def test_stub_jobs_succeed(self):
        engine = self.make_engine()
        jobs = [BatchJob(task_type="unknown_task") for _ in range(3)]
        summary = await engine.run(jobs, batch_name="test_batch")
        assert summary.total == 3
        assert summary.successful == 3
        assert summary.failed == 0
        assert summary.success_rate_pct == 100.0

    @pytest.mark.asyncio
    async def test_registered_handler_called(self):
        engine = self.make_engine()
        called = []

        async def my_handler(job: BatchJob) -> dict:
            called.append(job.task_type)
            return {"processed": True}

        engine.register_handler("custom_task", my_handler)
        jobs = [BatchJob(task_type="custom_task") for _ in range(3)]
        summary = await engine.run(jobs)
        assert len(called) == 3
        assert summary.successful == 3

    @pytest.mark.asyncio
    async def test_failing_handler_marks_job_failed(self):
        engine = BatchEngine(concurrency=2, rate_limit_per_minute=60, max_retries=0)

        async def bad_handler(job: BatchJob) -> dict:
            raise RuntimeError("Handler exploded")

        engine.register_handler("bad_task", bad_handler)
        jobs = [BatchJob(task_type="bad_task")]
        summary = await engine.run(jobs)
        assert summary.failed == 1
        assert len(summary.errors) == 1

    @pytest.mark.asyncio
    async def test_batch_name_preserved(self):
        engine = self.make_engine()
        summary = await engine.run([BatchJob(task_type="x")], batch_name="my_batch")
        assert summary.batch_name == "my_batch"

    @pytest.mark.asyncio
    async def test_priority_ordering(self):
        engine = self.make_engine()
        order = []

        async def track_handler(job: BatchJob) -> dict:
            order.append(job.priority)
            return {}

        engine.register_handler("track", track_handler)
        jobs = [
            BatchJob(task_type="track", priority=10),
            BatchJob(task_type="track", priority=1),
            BatchJob(task_type="track", priority=5),
        ]
        await engine.run(jobs)
        # Jobs sorted by priority ascending (1=highest)
        assert order[0] == 1

    @pytest.mark.asyncio
    async def test_get_summaries(self):
        engine = self.make_engine()
        await engine.run([BatchJob(task_type="a")], batch_name="batch_1")
        await engine.run([BatchJob(task_type="b")], batch_name="batch_2")
        summaries = engine.get_summaries()
        assert len(summaries) == 2
        names = [s["batch_name"] for s in summaries]
        assert "batch_1" in names
        assert "batch_2" in names

    @pytest.mark.asyncio
    async def test_get_metrics_empty(self):
        engine = self.make_engine()
        metrics = engine.get_metrics()
        assert metrics == {"total_batches": 0}

    @pytest.mark.asyncio
    async def test_get_metrics_after_runs(self):
        engine = self.make_engine()
        await engine.run([BatchJob(task_type="x"), BatchJob(task_type="y")])
        metrics = engine.get_metrics()
        assert metrics["total_batches"] == 1
        assert metrics["total_jobs"] == 2
        assert metrics["total_successful"] == 2
        assert metrics["overall_success_rate_pct"] == 100.0

    @pytest.mark.asyncio
    async def test_run_intelligence_scan(self):
        engine = self.make_engine()
        topics = ["Saudi football", "Saudi Pro League", "Transfer news"]
        summary = await engine.run_intelligence_scan(topics)
        assert summary.total == 3
        assert summary.batch_name == "intelligence_scan"

    @pytest.mark.asyncio
    async def test_run_content_batch(self):
        engine = self.make_engine()
        items = [{"task_type": "news", "topic": "match"}, {"task_type": "news", "topic": "transfer"}]
        summary = await engine.run_content_batch(items)
        assert summary.total == 2
        assert summary.batch_name == "content_batch"

    @pytest.mark.asyncio
    async def test_run_persona_analysis(self):
        engine = self.make_engine()
        contexts = [{"persona": "khalid"}, {"persona": "sara"}]
        summary = await engine.run_persona_analysis(contexts)
        assert summary.total == 2
        assert summary.batch_name == "persona_analysis"

    @pytest.mark.asyncio
    async def test_run_batch_reporting(self):
        engine = self.make_engine()
        states = [{"run_id": "r1"}, {"run_id": "r2"}]
        summary = await engine.run_batch_reporting(states)
        assert summary.total == 2
        assert summary.batch_name == "batch_reporting"

    @pytest.mark.asyncio
    async def test_concurrency_limit_respected(self):
        engine = BatchEngine(concurrency=2, rate_limit_per_minute=100, max_retries=0)
        concurrent = [0]
        max_concurrent = [0]

        async def slow_handler(job: BatchJob) -> dict:
            concurrent[0] += 1
            max_concurrent[0] = max(max_concurrent[0], concurrent[0])
            await asyncio.sleep(0.01)
            concurrent[0] -= 1
            return {}

        engine.register_handler("slow", slow_handler)
        jobs = [BatchJob(task_type="slow") for _ in range(6)]
        await engine.run(jobs)
        assert max_concurrent[0] <= 2

    @pytest.mark.asyncio
    async def test_duration_tracked(self):
        engine = self.make_engine()
        summary = await engine.run([BatchJob(task_type="x")])
        assert summary.total_duration_ms >= 0

    @pytest.mark.asyncio
    async def test_batch_id_unique(self):
        engine = self.make_engine()
        s1 = await engine.run([BatchJob(task_type="x")])
        s2 = await engine.run([BatchJob(task_type="x")])
        assert s1.batch_id != s2.batch_id
