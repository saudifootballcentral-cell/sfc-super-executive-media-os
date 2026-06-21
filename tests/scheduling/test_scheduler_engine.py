"""Tests for the SFC Scheduler Engine."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

import pytest

from sfc.scheduler.calendar import CronExpression, CycleCalendar
from sfc.scheduler.engine import SFCScheduler
from sfc.scheduler.jobs import (
    JobDefinition,
    JobPriority,
    JobStatus,
    JobType,
    make_daily_brief_job,
    make_trend_scan_job,
)
from sfc.scheduler.triggers import TriggerCondition, TriggerConfig, TriggerType


# ---------------------------------------------------------------------------
# CronExpression tests
# ---------------------------------------------------------------------------


class TestCronExpression:
    def test_invalid_expression_raises(self):
        with pytest.raises(ValueError):
            CronExpression("0 7 * *")  # only 4 fields

    def test_daily_at_7am(self):
        expr = CronExpression("0 7 * * *")
        dt = datetime(2025, 1, 15, 7, 0, 0)
        assert expr.matches(dt) is True

    def test_daily_at_7am_wrong_minute(self):
        expr = CronExpression("0 7 * * *")
        dt = datetime(2025, 1, 15, 7, 1, 0)
        assert expr.matches(dt) is False

    def test_every_30_minutes(self):
        expr = CronExpression("*/30 * * * *")
        assert expr.matches(datetime(2025, 1, 1, 0, 0)) is True
        assert expr.matches(datetime(2025, 1, 1, 0, 30)) is True
        assert expr.matches(datetime(2025, 1, 1, 0, 15)) is False

    def test_monday_at_9am(self):
        expr = CronExpression("0 9 * * 1")
        monday = datetime(2025, 1, 6, 9, 0)   # Jan 6, 2025 is Monday
        tuesday = datetime(2025, 1, 7, 9, 0)
        assert expr.matches(monday) is True
        assert expr.matches(tuesday) is False

    def test_comma_list_hours(self):
        expr = CronExpression("0 8,18 * * *")
        assert expr.matches(datetime(2025, 1, 1, 8, 0)) is True
        assert expr.matches(datetime(2025, 1, 1, 18, 0)) is True
        assert expr.matches(datetime(2025, 1, 1, 12, 0)) is False

    def test_first_of_month(self):
        expr = CronExpression("0 0 1 * *")
        assert expr.matches(datetime(2025, 3, 1, 0, 0)) is True
        assert expr.matches(datetime(2025, 3, 2, 0, 0)) is False

    def test_range_in_field(self):
        expr = CronExpression("0 9-17 * * *")
        assert expr.matches(datetime(2025, 1, 1, 9, 0)) is True
        assert expr.matches(datetime(2025, 1, 1, 17, 0)) is True
        assert expr.matches(datetime(2025, 1, 1, 8, 0)) is False

    def test_next_run_is_future(self):
        expr = CronExpression("0 7 * * *")
        now = datetime.utcnow()
        next_run = expr.next_run(now)
        assert next_run > now

    def test_next_run_interval(self):
        expr = CronExpression("*/30 * * * *")
        anchor = datetime(2025, 6, 1, 10, 0)
        nxt = expr.next_run(anchor)
        assert nxt == datetime(2025, 6, 1, 10, 30)


class TestCycleCalendar:
    def test_next_daily_is_in_future(self):
        target = CycleCalendar.next_daily(hour=7)
        assert target > datetime.utcnow()

    def test_next_weekly_is_in_future(self):
        target = CycleCalendar.next_weekly(weekday=0)
        assert target > datetime.utcnow()

    def test_next_monthly_is_in_future(self):
        target = CycleCalendar.next_monthly(day=1)
        assert target > datetime.utcnow()

    def test_next_quarterly_is_in_future(self):
        target = CycleCalendar.next_quarterly()
        assert target > datetime.utcnow()

    def test_next_annual_is_in_future(self):
        target = CycleCalendar.next_annual()
        assert target > datetime.utcnow()

    def test_seconds_until_positive(self):
        future = datetime.utcnow() + timedelta(hours=1)
        secs = CycleCalendar.seconds_until(future)
        assert secs > 0

    def test_seconds_until_past_returns_zero(self):
        past = datetime.utcnow() - timedelta(hours=1)
        secs = CycleCalendar.seconds_until(past)
        assert secs == 0.0


# ---------------------------------------------------------------------------
# SFCScheduler tests
# ---------------------------------------------------------------------------


class TestSFCScheduler:
    def make_scheduler(self) -> SFCScheduler:
        return SFCScheduler(tick_interval=99999)  # no auto-tick in tests

    def test_add_job(self):
        scheduler = self.make_scheduler()
        job = make_daily_brief_job()
        job_id = scheduler.add_job(job)
        assert job_id
        assert scheduler.get_job(job_id) is not None

    def test_add_and_list_jobs(self):
        scheduler = self.make_scheduler()
        scheduler.add_job(make_daily_brief_job())
        scheduler.add_job(make_trend_scan_job())
        jobs = scheduler.list_jobs()
        assert len(jobs) == 2

    def test_remove_job(self):
        scheduler = self.make_scheduler()
        job_id = scheduler.add_job(make_daily_brief_job())
        assert scheduler.remove_job(job_id) is True
        assert scheduler.get_job(job_id) is None

    def test_remove_nonexistent_job(self):
        scheduler = self.make_scheduler()
        assert scheduler.remove_job("nonexistent") is False

    def test_pause_and_resume_job(self):
        scheduler = self.make_scheduler()
        job_id = scheduler.add_job(make_daily_brief_job())
        assert scheduler.pause_job(job_id) is True
        job = scheduler.get_job(job_id)
        assert job.status == JobStatus.PAUSED
        assert job.enabled is False

        assert scheduler.resume_job(job_id) is True
        job = scheduler.get_job(job_id)
        assert job.status == JobStatus.PENDING
        assert job.enabled is True

    def test_pause_nonexistent_returns_false(self):
        scheduler = self.make_scheduler()
        assert scheduler.pause_job("missing") is False

    def test_resume_nonexistent_returns_false(self):
        scheduler = self.make_scheduler()
        assert scheduler.resume_job("missing") is False

    def test_add_trigger(self):
        scheduler = self.make_scheduler()
        trigger = TriggerConfig(
            trigger_type=TriggerType.MANUAL,
            name="test",
            job_task_type="test",
        )
        trigger_id = scheduler.add_trigger(trigger)
        assert trigger_id == trigger.trigger_id
        assert len(scheduler._triggers) == 1

    def test_get_health_structure(self):
        scheduler = self.make_scheduler()
        scheduler.add_job(make_daily_brief_job())
        health = scheduler.get_health()
        assert "total_jobs" in health
        assert "enabled_jobs" in health
        assert health["total_jobs"] == 1

    def test_get_execution_report_structure(self):
        scheduler = self.make_scheduler()
        scheduler.add_job(make_daily_brief_job())
        report = scheduler.get_execution_report()
        assert "scheduler" in report
        assert "jobs" in report
        assert "recent_history" in report
        assert len(report["jobs"]) == 1

    def test_recover_missed_jobs_marks_missed(self):
        scheduler = self.make_scheduler()
        job = make_trend_scan_job()
        job_id = scheduler.add_job(job)
        # Force next_run_at to be in the past
        job_obj = scheduler.get_job(job_id)
        job_obj.next_run_at = datetime.utcnow() - timedelta(minutes=60)
        missed = scheduler.recover_missed_jobs()
        assert job_id in missed
        assert scheduler.get_job(job_id).status == JobStatus.MISSED

    def test_register_handler(self):
        scheduler = self.make_scheduler()

        async def my_handler(job):
            return {"ok": True}

        scheduler.register_handler("my_task", my_handler)
        assert "my_task" in scheduler._handlers

    @pytest.mark.asyncio
    async def test_evaluate_triggers_fires_job(self):
        scheduler = self.make_scheduler()
        trigger = TriggerConfig(
            trigger_type=TriggerType.MANUAL,
            name="always_fires",
            conditions=[TriggerCondition(condition_type="always")],
            job_task_type="manual_test",
            cooldown_seconds=0,
        )
        scheduler.add_trigger(trigger)
        fired = await scheduler.evaluate_triggers({})
        assert len(fired) == 1

    @pytest.mark.asyncio
    async def test_evaluate_triggers_no_fire_on_cooldown(self):
        scheduler = self.make_scheduler()
        trigger = TriggerConfig(
            trigger_type=TriggerType.MANUAL,
            name="on_cooldown",
            conditions=[TriggerCondition(condition_type="always")],
            job_task_type="test",
            cooldown_seconds=9999,
            last_fired_at=datetime.utcnow(),
        )
        scheduler.add_trigger(trigger)
        fired = await scheduler.evaluate_triggers({})
        assert len(fired) == 0

    @pytest.mark.asyncio
    async def test_start_and_stop(self):
        scheduler = self.make_scheduler()
        await scheduler.start()
        assert scheduler._state.started_at is not None
        await scheduler.stop()
        assert scheduler._state.started_at is None

    @pytest.mark.asyncio
    async def test_start_idempotent(self):
        scheduler = self.make_scheduler()
        await scheduler.start()
        started_at = scheduler._state.started_at
        await scheduler.start()  # second call should be no-op
        assert scheduler._state.started_at == started_at
        await scheduler.stop()

    @pytest.mark.asyncio
    async def test_execute_job_with_handler(self):
        scheduler = self.make_scheduler()
        results = []

        async def handler(job):
            results.append(job.task_type)
            return {"done": True}

        scheduler.register_handler("my_task", handler)
        job = JobDefinition(
            name="run_me",
            job_type=JobType.ONE_TIME,
            task_type="my_task",
        )
        job_id = scheduler.add_job(job)
        record = await scheduler._execute_job(scheduler.get_job(job_id))
        assert record.status == JobStatus.COMPLETED
        assert results == ["my_task"]

    @pytest.mark.asyncio
    async def test_execute_job_without_handler_stubs(self):
        scheduler = self.make_scheduler()
        job = JobDefinition(
            name="stubbed",
            job_type=JobType.ONE_TIME,
            task_type="no_handler_here",
        )
        job_id = scheduler.add_job(job)
        record = await scheduler._execute_job(scheduler.get_job(job_id))
        assert record.status == JobStatus.COMPLETED
        assert record.result_summary.get("stub") is True

    @pytest.mark.asyncio
    async def test_execute_job_failure_increments_counter(self):
        scheduler = self.make_scheduler()

        async def failing_handler(job):
            raise RuntimeError("Test failure")

        scheduler.register_handler("fail_task", failing_handler)
        job = JobDefinition(
            name="will_fail",
            job_type=JobType.ONE_TIME,
            task_type="fail_task",
        )
        job_id = scheduler.add_job(job)
        record = await scheduler._execute_job(scheduler.get_job(job_id))
        assert record.status == JobStatus.FAILED
        assert "Test failure" in record.error
