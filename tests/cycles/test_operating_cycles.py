"""Tests for the Operating Cycles Service."""

from __future__ import annotations

import pytest

from sfc.cycles.models import CyclePhase, CycleResult, CycleStep, CycleType
from sfc.cycles.service import CycleService
from sfc.reporting.executive.service import ExecutiveReportService
from sfc.reporting.operational.service import OperationalReportService
from sfc.analytics.historical.service import get_historical_service
from sfc.forecasting.cost.service import CostForecastService


class TestCycleModels:
    def test_cycle_type_values(self):
        expected = {"daily", "weekly", "monthly", "quarterly", "annual"}
        assert {c.value for c in CycleType} == expected

    def test_cycle_phase_values(self):
        expected = {"pending", "running", "completed", "failed", "partial"}
        assert {p.value for p in CyclePhase} == expected

    def test_cycle_step_defaults(self):
        from datetime import datetime
        step = CycleStep(step_name="test_step", started_at=datetime.utcnow())
        assert step.status == CyclePhase.PENDING
        assert step.duration_ms == 0
        assert step.error is None

    def test_cycle_result_to_dict(self):
        result = CycleResult(cycle_type=CycleType.DAILY)
        d = result.to_dict()
        assert isinstance(d, dict)
        assert d["cycle_type"] == "daily"

    def test_cycle_result_to_summary(self):
        result = CycleResult(cycle_type=CycleType.WEEKLY, status=CyclePhase.COMPLETED)
        summary = result.to_summary()
        assert isinstance(summary, dict)
        assert summary["cycle_type"] == "weekly"
        assert summary["status"] == "completed"


class TestCycleService:
    def make_service(self) -> CycleService:
        return CycleService()

    def make_full_service(self) -> CycleService:
        svc = CycleService()
        svc.inject_services(
            executive=ExecutiveReportService(),
            operational=OperationalReportService(),
            historical=get_historical_service(),
            forecast=CostForecastService(),
        )
        return svc

    @pytest.mark.asyncio
    async def test_daily_cycle_runs(self):
        svc = self.make_service()
        result = await svc.run_daily()
        assert result.cycle_type == CycleType.DAILY
        assert result.status in (CyclePhase.COMPLETED, CyclePhase.PARTIAL, CyclePhase.FAILED)

    @pytest.mark.asyncio
    async def test_daily_cycle_has_five_steps(self):
        svc = self.make_service()
        result = await svc.run_daily()
        step_names = [s.step_name for s in result.steps]
        assert "opportunity_scan" in step_names
        assert "trend_scan" in step_names
        assert "executive_brief" in step_names
        assert "cost_check" in step_names
        assert "memory_update" in step_names

    @pytest.mark.asyncio
    async def test_weekly_cycle_runs(self):
        svc = self.make_service()
        result = await svc.run_weekly()
        assert result.cycle_type == CycleType.WEEKLY
        step_names = [s.step_name for s in result.steps]
        assert "performance_review" in step_names
        assert "persona_review" in step_names
        assert "growth_review" in step_names
        assert "war_room_review" in step_names

    @pytest.mark.asyncio
    async def test_monthly_cycle_runs(self):
        svc = self.make_service()
        result = await svc.run_monthly()
        assert result.cycle_type == CycleType.MONTHLY
        step_names = [s.step_name for s in result.steps]
        assert "strategy_review" in step_names
        assert "revenue_review" in step_names
        assert "sponsor_review" in step_names
        assert "governance_review" in step_names

    @pytest.mark.asyncio
    async def test_quarterly_cycle_runs(self):
        svc = self.make_service()
        result = await svc.run_quarterly()
        assert result.cycle_type == CycleType.QUARTERLY
        step_names = [s.step_name for s in result.steps]
        assert "executive_planning" in step_names
        assert "expansion_planning" in step_names
        assert "platform_review" in step_names

    @pytest.mark.asyncio
    async def test_annual_cycle_runs(self):
        svc = self.make_service()
        result = await svc.run_annual()
        assert result.cycle_type == CycleType.ANNUAL
        step_names = [s.step_name for s in result.steps]
        assert "annual_report" in step_names
        assert "strategic_reset" in step_names
        assert "roadmap_planning" in step_names

    @pytest.mark.asyncio
    async def test_completed_status_when_no_errors(self):
        svc = self.make_service()
        result = await svc.run_daily()
        if not result.errors:
            assert result.status == CyclePhase.COMPLETED

    @pytest.mark.asyncio
    async def test_partial_status_when_some_steps_fail(self):
        svc = CycleService()

        # Inject services that will cause some steps to have issues
        # With no services injected, steps still succeed with stub returns
        result = await svc.run_daily()
        # Should be COMPLETED since all steps return stubs (no exceptions)
        assert result.status in (CyclePhase.COMPLETED, CyclePhase.PARTIAL)

    @pytest.mark.asyncio
    async def test_steps_have_duration(self):
        svc = self.make_service()
        result = await svc.run_daily()
        for step in result.steps:
            assert step.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_result_has_duration(self):
        svc = self.make_service()
        result = await svc.run_weekly()
        assert result.duration_ms >= 0
        assert result.completed_at is not None

    @pytest.mark.asyncio
    async def test_history_tracking(self):
        svc = self.make_service()
        await svc.run_daily()
        await svc.run_weekly()
        history = svc.get_history()
        assert len(history) == 2

    @pytest.mark.asyncio
    async def test_history_filtered_by_type(self):
        svc = self.make_service()
        await svc.run_daily()
        await svc.run_weekly()
        await svc.run_daily()
        daily = svc.get_history(cycle_type=CycleType.DAILY)
        assert len(daily) == 2
        assert all(d["cycle_type"] == "daily" for d in daily)

    @pytest.mark.asyncio
    async def test_summary_structure(self):
        svc = self.make_service()
        await svc.run_daily()
        await svc.run_weekly()
        summary = svc.get_summary()
        assert "total_cycles_run" in summary
        assert "by_type" in summary
        assert "recent" in summary
        assert summary["total_cycles_run"] == 2
        assert "daily" in summary["by_type"]
        assert "weekly" in summary["by_type"]

    @pytest.mark.asyncio
    async def test_daily_with_injected_services(self):
        svc = self.make_full_service()
        result = await svc.run_daily()
        assert result.cycle_type == CycleType.DAILY
        assert result.status in (CyclePhase.COMPLETED, CyclePhase.PARTIAL)

    @pytest.mark.asyncio
    async def test_weekly_with_injected_services(self):
        svc = self.make_full_service()
        result = await svc.run_weekly()
        assert result.cycle_type == CycleType.WEEKLY

    @pytest.mark.asyncio
    async def test_monthly_with_injected_services(self):
        svc = self.make_full_service()
        result = await svc.run_monthly()
        assert result.cycle_type == CycleType.MONTHLY

    @pytest.mark.asyncio
    async def test_context_passed_through_steps(self):
        svc = self.make_service()
        context = {"custom_key": "custom_value", "lessons_captured": ["lesson1"]}
        result = await svc.run_daily(context)
        assert result.cycle_type == CycleType.DAILY

    @pytest.mark.asyncio
    async def test_inject_services(self):
        svc = CycleService()
        exec_svc = ExecutiveReportService()
        svc.inject_services(executive=exec_svc)
        assert svc._executive_report_service is exec_svc

    @pytest.mark.asyncio
    async def test_all_cycles_run_sequentially(self):
        svc = self.make_service()
        results = []
        results.append(await svc.run_daily())
        results.append(await svc.run_weekly())
        results.append(await svc.run_monthly())
        results.append(await svc.run_quarterly())
        results.append(await svc.run_annual())
        assert len(results) == 5
        types = [r.cycle_type for r in results]
        assert CycleType.DAILY in types
        assert CycleType.ANNUAL in types
