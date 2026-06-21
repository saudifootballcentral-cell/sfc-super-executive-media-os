"""Tests for scheduler job definitions and factory helpers."""

from __future__ import annotations

from datetime import datetime

import pytest

from sfc.scheduler.jobs import (
    JobDefinition,
    JobPriority,
    JobRecord,
    JobStatus,
    JobType,
    make_cost_guard_job,
    make_daily_brief_job,
    make_trend_scan_job,
    make_weekly_report_job,
)


class TestJobDefinition:
    def test_defaults(self):
        job = JobDefinition(name="test", job_type=JobType.INTERVAL, task_type="test_task")
        assert job.status == JobStatus.PENDING
        assert job.priority == JobPriority.MEDIUM
        assert job.enabled is True
        assert job.max_retries == 3
        assert job.run_count == 0
        assert job.failure_count == 0
        assert job.job_id  # uuid generated

    def test_all_job_types(self):
        for jt in JobType:
            job = JobDefinition(name="x", job_type=jt, task_type="t")
            assert job.job_type == jt

    def test_all_statuses(self):
        job = JobDefinition(name="x", job_type=JobType.ONE_TIME, task_type="t")
        for status in JobStatus:
            job.status = status
            assert job.status == status

    def test_all_priorities(self):
        for p in JobPriority:
            job = JobDefinition(name="x", job_type=JobType.INTERVAL, task_type="t", priority=p)
            assert job.priority == p

    def test_cron_job_fields(self):
        job = JobDefinition(
            name="cron_job",
            job_type=JobType.CRON,
            task_type="report",
            cron_expression="0 7 * * *",
        )
        assert job.cron_expression == "0 7 * * *"

    def test_interval_job_fields(self):
        job = JobDefinition(
            name="interval",
            job_type=JobType.INTERVAL,
            task_type="scan",
            interval_seconds=1800,
        )
        assert job.interval_seconds == 1800

    def test_one_time_job_fields(self):
        run_at = datetime(2030, 1, 1, 9, 0, 0)
        job = JobDefinition(
            name="once",
            job_type=JobType.ONE_TIME,
            task_type="brief",
            run_at=run_at,
        )
        assert job.run_at == run_at

    def test_ai_cost_job_fields(self):
        job = JobDefinition(
            name="cost_guard",
            job_type=JobType.AI_COST,
            task_type="cost_alert",
            cost_threshold_usd=75.0,
        )
        assert job.cost_threshold_usd == 75.0

    def test_war_room_job_fields(self):
        job = JobDefinition(
            name="match",
            job_type=JobType.WAR_ROOM,
            task_type="match_day",
            war_room_type="match_day",
        )
        assert job.war_room_type == "match_day"

    def test_persona_job_fields(self):
        job = JobDefinition(
            name="persona",
            job_type=JobType.PERSONA,
            task_type="persona_report",
            persona_id="persona_001",
        )
        assert job.persona_id == "persona_001"

    def test_unique_job_ids(self):
        j1 = JobDefinition(name="a", job_type=JobType.INTERVAL, task_type="t")
        j2 = JobDefinition(name="b", job_type=JobType.INTERVAL, task_type="t")
        assert j1.job_id != j2.job_id


class TestJobRecord:
    def test_defaults(self):
        record = JobRecord(
            job_id="abc",
            job_name="test_job",
            task_type="news",
            started_at=datetime.utcnow(),
        )
        assert record.status == JobStatus.PENDING
        assert record.duration_ms == 0
        assert record.retry_count == 0
        assert record.error is None

    def test_record_id_generated(self):
        r = JobRecord(job_id="x", job_name="y", task_type="z", started_at=datetime.utcnow())
        assert r.record_id


class TestJobFactories:
    def test_daily_brief_job(self):
        job = make_daily_brief_job()
        assert job.name == "daily_executive_brief"
        assert job.job_type == JobType.CRON
        assert job.task_type == "executive_brief"
        assert job.cron_expression == "0 7 * * *"
        assert job.priority == JobPriority.HIGH
        assert job.payload.get("report_type") == "daily"

    def test_trend_scan_job_default(self):
        job = make_trend_scan_job()
        assert job.name == "trend_scan"
        assert job.job_type == JobType.INTERVAL
        assert job.task_type == "trend_scan"
        assert job.interval_seconds == 30 * 60  # 30 minutes

    def test_trend_scan_job_custom(self):
        job = make_trend_scan_job(interval_minutes=60)
        assert job.interval_seconds == 3600

    def test_weekly_report_job(self):
        job = make_weekly_report_job()
        assert job.name == "weekly_performance_report"
        assert job.job_type == JobType.CRON
        assert job.cron_expression == "0 9 * * 1"
        assert job.priority == JobPriority.HIGH

    def test_cost_guard_job_default(self):
        job = make_cost_guard_job()
        assert job.name == "ai_cost_guard"
        assert job.job_type == JobType.AI_COST
        assert job.task_type == "cost_alert"
        assert job.cost_threshold_usd == 50.0

    def test_cost_guard_job_custom(self):
        job = make_cost_guard_job(threshold_usd=200.0)
        assert job.cost_threshold_usd == 200.0
        assert job.payload.get("threshold_usd") == 200.0
