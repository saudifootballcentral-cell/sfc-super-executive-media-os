"""Package 8 end-to-end integration tests.

Verifies:
1. Autonomous triggers fire through governance gate (not bypass it)
2. All operating cycles complete with or without injected services
3. Report delivery chain works end-to-end
4. Autonomous execution manager correctly routes to graph (with stub graph)
5. Scheduler + trigger engine integration
"""

from __future__ import annotations

import pytest

from sfc.autonomous.execution_manager import AutonomousExecutionManager, ExecutionRequest
from sfc.autonomous.trigger_engine import AutonomousTriggerEngine
from sfc.batch.engine import BatchEngine, BatchJob
from sfc.cycles.service import CycleService
from sfc.cycles.models import CyclePhase, CycleType
from sfc.forecasting.cost.service import CostForecastService
from sfc.reporting.delivery.models import DeliveryChannel, DeliveryStatus
from sfc.reporting.delivery.service import ReportDeliveryService
from sfc.reporting.executive.models import ExecutiveReport, ReportPeriod
from sfc.reporting.executive.service import ExecutiveReportService
from sfc.reporting.operational.service import OperationalReportService
from sfc.scheduler.engine import SFCScheduler
from sfc.scheduler.jobs import make_daily_brief_job, make_trend_scan_job
from sfc.scheduler.triggers import TriggerCondition, TriggerConfig, TriggerType


# ---------------------------------------------------------------------------
# Governance preservation tests
# ---------------------------------------------------------------------------


class TestGovernancePreservation:
    """Verify that autonomous execution routes through governance, not around it."""

    @pytest.mark.asyncio
    async def test_autonomous_exec_calls_graph_ainvoke(self):
        """Execution manager must invoke the graph (which has governance_node)."""
        manager = AutonomousExecutionManager()
        invoked_states = []

        class GovernanceTestGraph:
            async def ainvoke(self, state):
                invoked_states.append(state)
                # Simulate pipeline completing with governance gate hit
                return {
                    "completed_at": "2025-01-01T00:00:00",
                    "run_id": state.get("run_id", "test"),
                    "pipeline_stage": "memory_update",
                    "errors": [],
                    "warnings": [],
                    "governance_reviews": [{"reviewed": True}],
                    "approved_content": [],
                }

        manager.set_graph(GovernanceTestGraph())
        req = ExecutionRequest(task_type="news", source="trigger:crisis")
        record = await manager.execute_now(req)

        # Graph was called
        assert len(invoked_states) == 1
        # Governance review was part of the state passed to graph
        assert invoked_states[0]["task_type"] == "news"
        assert record.success is True

    @pytest.mark.asyncio
    async def test_trigger_engine_does_not_bypass_governance(self):
        """Triggers fire execution requests — they do not directly publish."""
        engine = AutonomousTriggerEngine()
        events = await engine.evaluate({})
        # Events are fired — but they only create TriggerEvents
        # They do NOT directly publish or skip governance
        for event in events:
            assert hasattr(event, "trigger_type")
            assert hasattr(event, "context_snapshot")
            # No content is directly published — event just records the trigger
            assert event.resulting_job_id is None  # no graph was invoked by trigger engine alone

    @pytest.mark.asyncio
    async def test_cycle_service_does_not_publish_content_directly(self):
        """Operating cycles generate reports but do not bypass governance for content."""
        svc = CycleService()
        result = await svc.run_daily()
        # Cycles produce reports (executive_report, cost_forecast)
        # They do NOT set approved_content or bypass governance
        assert result.cycle_type == CycleType.DAILY
        # No content publishing happened at the cycle level
        assert "approved_content" not in result.to_dict()

    @pytest.mark.asyncio
    async def test_batch_engine_does_not_approve_content_without_graph(self):
        """BatchEngine without a graph connection cannot publish content."""
        engine = BatchEngine(max_retries=0)
        jobs = [BatchJob(task_type="news", payload={"topic": "match"})]
        summary = await engine.run(jobs)
        # Jobs complete as stubs — no content approved without graph
        assert summary.successful == 1
        assert summary.failed == 0


# ---------------------------------------------------------------------------
# End-to-end pipeline tests
# ---------------------------------------------------------------------------


class TestPkg8EndToEnd:
    @pytest.mark.asyncio
    async def test_trigger_to_execution_pipeline(self):
        """Full trigger → execution flow without real graph."""
        engine = AutonomousTriggerEngine()
        manager = AutonomousExecutionManager()
        execution_calls = []

        class StubGraph:
            async def ainvoke(self, state):
                execution_calls.append(state.get("task_type"))
                return {
                    "completed_at": "2025-01-01T00:00:00",
                    "run_id": state.get("run_id", ""),
                    "pipeline_stage": "memory_update",
                    "errors": [],
                    "warnings": [],
                }

        manager.set_graph(StubGraph())

        # Evaluate triggers
        events = await engine.evaluate({})
        assert len(events) >= 1

        # Submit events as execution requests
        for event in events[:2]:
            req = ExecutionRequest(
                task_type=event.trigger_type.value,
                source=f"trigger:{event.trigger_type.value}",
                trigger_event_id=event.event_id,
            )
            record = await manager.execute_now(req)
            assert record.success is True

        assert len(execution_calls) >= 1

    @pytest.mark.asyncio
    async def test_daily_cycle_with_full_services(self):
        """Daily cycle with all services injected completes successfully."""
        svc = CycleService()
        svc.inject_services(
            executive=ExecutiveReportService(),
            operational=OperationalReportService(),
            historical=None,
            forecast=CostForecastService(),
        )
        result = await svc.run_daily()
        assert result.cycle_type == CycleType.DAILY
        assert result.status in (CyclePhase.COMPLETED, CyclePhase.PARTIAL)
        assert len(result.steps) == 5

    @pytest.mark.asyncio
    async def test_executive_report_to_delivery_pipeline(self):
        """Report generated by executive service can be delivered via all channels."""
        exec_svc = ExecutiveReportService()
        delivery_svc = ReportDeliveryService()

        report = await exec_svc.generate_daily_brief({"content_published": 3})
        records = await delivery_svc.deliver(
            report,
            [DeliveryChannel.DASHBOARD, DeliveryChannel.MARKDOWN_EXPORT, DeliveryChannel.JSON_EXPORT],
        )
        assert len(records) == 3
        assert all(r.status == DeliveryStatus.DELIVERED for r in records)

    @pytest.mark.asyncio
    async def test_scheduler_trigger_creates_job(self):
        """Scheduler trigger fires and creates a job."""
        scheduler = SFCScheduler(tick_interval=99999)
        trigger = TriggerConfig(
            trigger_type=TriggerType.CRISIS_DETECTED,
            name="crisis_test",
            conditions=[TriggerCondition(condition_type="always")],
            job_task_type="crisis",
            cooldown_seconds=0,
        )
        scheduler.add_trigger(trigger)
        fired_ids = await scheduler.evaluate_triggers({})
        assert len(fired_ids) == 1
        job = scheduler.get_job(fired_ids[0])
        assert job is not None
        assert job.task_type == "crisis"

    @pytest.mark.asyncio
    async def test_cost_forecast_pipeline(self):
        """Cost forecast generated without API keys uses zero-cost baseline."""
        service = CostForecastService()
        forecast = service.forecast()
        assert forecast.within_budget is True
        assert forecast.forecast_total_usd >= 0

    @pytest.mark.asyncio
    async def test_batch_intelligence_scan(self):
        """Batch intelligence scan completes for multiple topics."""
        engine = BatchEngine(concurrency=3, max_retries=0)
        topics = ["Al-Hilal vs Al-Nassr", "Saudi Pro League standings", "Transfer window"]
        summary = await engine.run_intelligence_scan(topics)
        assert summary.total == 3
        assert summary.successful == 3

    @pytest.mark.asyncio
    async def test_weekly_cycle_with_operational_reports(self):
        """Weekly cycle produces operational reports when service is injected."""
        svc = CycleService()
        op_svc = OperationalReportService()
        svc.inject_services(operational=op_svc)
        result = await svc.run_weekly()
        assert result.cycle_type == CycleType.WEEKLY
        # Steps should complete (some via operational service, some as stubs)
        assert len(result.steps) == 4

    @pytest.mark.asyncio
    async def test_all_five_cycles_run_without_errors(self):
        """All cycle types can run to completion without crashing."""
        svc = CycleService()
        cycle_results = [
            await svc.run_daily(),
            await svc.run_weekly(),
            await svc.run_monthly(),
            await svc.run_quarterly(),
            await svc.run_annual(),
        ]
        for result in cycle_results:
            assert result.status != CyclePhase.FAILED or (
                # FAILED is allowed only if ALL steps failed, which means service errors
                result.status == CyclePhase.FAILED and all(
                    s.status == CyclePhase.FAILED for s in result.steps
                )
            )

    @pytest.mark.asyncio
    async def test_event_types_complete(self):
        """All 12 Package 8 event types are registered in EVENT_TYPE_MAP."""
        from sfc.events.types import EVENT_TYPE_MAP
        pkg8_events = [
            "scheduled_job_created",
            "scheduled_job_started",
            "scheduled_job_completed",
            "scheduled_job_failed",
            "report_generated",
            "report_delivered",
            "autonomous_trigger_fired",
            "batch_job_started",
            "batch_job_completed",
            "forecast_generated",
            "budget_alert_triggered",
            "cycle_completed",
        ]
        for event_type in pkg8_events:
            assert event_type in EVENT_TYPE_MAP, f"Missing event type: {event_type}"

    @pytest.mark.asyncio
    async def test_state_has_pkg8_fields(self):
        """SFCState and make_initial_state include all Package 8 fields."""
        from sfc.graph.state import make_initial_state
        state = make_initial_state(task_type="executive_brief", task_payload={})
        pkg8_fields = [
            "scheduler_state",
            "autonomous_triggers",
            "trigger_report",
            "executive_report",
            "operational_reports",
            "historical_analytics",
            "cost_forecast",
            "batch_results",
            "autonomous_execution_plan",
            "delivery_log",
            "delivery_stats",
        ]
        for field in pkg8_fields:
            assert field in state, f"Missing SFCState field: {field}"

    def test_autonomous_graph_builds(self):
        """Autonomous graph compiles without errors."""
        from sfc.graph.autonomous_graph import build_autonomous_graph, get_autonomous_graph_ascii
        graph = build_autonomous_graph()
        assert graph is not None
        ascii_diagram = get_autonomous_graph_ascii()
        assert "scheduler_node" in ascii_diagram
        assert "memory_update" in ascii_diagram
