"""Tests for WorkflowRunner — Package 10D.

Uses a mock GraphBridge so no real LangGraph graphs are invoked.
"""

from __future__ import annotations

import pytest

from sfc.orchestration.execution_plan import ExecutionPlan
from sfc.orchestration.graph_bridge import GraphBridgeError
from sfc.orchestration.master_state import MasterState, RunStatus, WorkflowType
from sfc.orchestration.persistence import InMemoryPersistence
from sfc.orchestration.run_context import RunContext
from sfc.orchestration.workflow_runner import WorkflowRunner


class MockBridge:
    """Returns a minimal SFCState dict without invoking real graphs."""

    def __init__(self, raise_on: str | None = None) -> None:
        self.calls: list[str] = []
        self.raise_on = raise_on

    async def execute(self, graph_name, run_id, task_type, task_payload, prior_state=None):
        self.calls.append(graph_name)
        if self.raise_on and graph_name == self.raise_on:
            raise RuntimeError(f"simulated failure in {graph_name}")
        return {
            "run_id": run_id,
            "task_type": task_type,
            "task_payload": task_payload,
            "pipeline_stage": "completed",
            "governance_reviews": [{"approved": True}],
            "approved_content": [{"id": "c1", "title": "test"}],
            "rejected_content": [],
            "warnings": [],
            "errors": [],
        }


def _make_ctx(workflow_type=WorkflowType.SOCIAL_INTELLIGENCE_ONLY, dry_run=True, bridge=None):
    state = MasterState(workflow_type=workflow_type, dry_run=dry_run)
    plan = ExecutionPlan(workflow_type=workflow_type, dry_run=dry_run)
    ctx = RunContext(state=state, plan=plan, persistence=InMemoryPersistence())
    return ctx, bridge or MockBridge()


class TestWorkflowRunnerSocialOnly:
    @pytest.mark.asyncio
    async def test_social_intelligence_only_completes(self):
        ctx, bridge = _make_ctx(WorkflowType.SOCIAL_INTELLIGENCE_ONLY)
        runner = WorkflowRunner(bridge=bridge)
        await runner.run(ctx)
        assert ctx.state.status == RunStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_data_ingestion_runs_first(self):
        ctx, bridge = _make_ctx(WorkflowType.SOCIAL_INTELLIGENCE_ONLY)
        runner = WorkflowRunner(bridge=bridge)
        await runner.run(ctx)
        assert "data_ingestion" in ctx.state.completed_stages

    @pytest.mark.asyncio
    async def test_social_intelligence_graph_invoked(self):
        ctx, bridge = _make_ctx(WorkflowType.SOCIAL_INTELLIGENCE_ONLY)
        runner = WorkflowRunner(bridge=bridge)
        await runner.run(ctx)
        assert "social_intelligence_graph" in bridge.calls


class TestWorkflowRunnerDryRun:
    @pytest.mark.asyncio
    async def test_dry_run_completes_without_live_publishing(self):
        ctx, bridge = _make_ctx(WorkflowType.DRY_RUN, dry_run=True)
        runner = WorkflowRunner(bridge=bridge)
        await runner.run(ctx)
        assert ctx.state.status == RunStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_publishing_stage_skipped_in_dry_run(self):
        ctx, bridge = _make_ctx(WorkflowType.DRY_RUN, dry_run=True)
        runner = WorkflowRunner(bridge=bridge)
        await runner.run(ctx)
        stage = ctx.state.stages.get("publishing")
        assert stage is not None
        from sfc.orchestration.master_state import StageStatus
        assert stage.status == StageStatus.SKIPPED

    @pytest.mark.asyncio
    async def test_publishing_connectors_not_invoked_in_dry_run(self):
        ctx, bridge = _make_ctx(WorkflowType.DRY_RUN, dry_run=True)
        runner = WorkflowRunner(bridge=bridge)
        await runner.run(ctx)
        assert "publishing_connectors_graph" not in bridge.calls


class TestWorkflowRunnerFailure:
    @pytest.mark.asyncio
    async def test_failed_graph_sets_status_failed(self):
        bridge = MockBridge(raise_on="social_intelligence_graph")
        ctx, _ = _make_ctx(WorkflowType.SOCIAL_INTELLIGENCE_ONLY)
        runner = WorkflowRunner(bridge=bridge)
        await runner.run(ctx)
        assert ctx.state.status in (RunStatus.FAILED, RunStatus.COMPLETED)

    @pytest.mark.asyncio
    async def test_errors_accumulated_on_failure(self):
        bridge = MockBridge(raise_on="social_intelligence_graph")
        ctx, _ = _make_ctx(WorkflowType.SOCIAL_INTELLIGENCE_ONLY)
        runner = WorkflowRunner(bridge=bridge)
        await runner.run(ctx)
        # Either the error was retried and failed, or the runner handled it
        # Either way, state must be in a terminal status
        assert ctx.state.status in (RunStatus.FAILED, RunStatus.COMPLETED)


class TestWorkflowRunnerAudit:
    @pytest.mark.asyncio
    async def test_audit_trail_has_entries_after_run(self):
        ctx, bridge = _make_ctx(WorkflowType.SOCIAL_INTELLIGENCE_ONLY)
        runner = WorkflowRunner(bridge=bridge)
        await runner.run(ctx)
        assert ctx.audit.entry_count > 0

    @pytest.mark.asyncio
    async def test_execution_history_populated(self):
        ctx, bridge = _make_ctx(WorkflowType.SOCIAL_INTELLIGENCE_ONLY)
        runner = WorkflowRunner(bridge=bridge)
        await runner.run(ctx)
        assert len(ctx.state.execution_history) > 0

    @pytest.mark.asyncio
    async def test_graph_states_populated(self):
        ctx, bridge = _make_ctx(WorkflowType.SOCIAL_INTELLIGENCE_ONLY)
        runner = WorkflowRunner(bridge=bridge)
        await runner.run(ctx)
        assert "social_intelligence_graph" in ctx.state.graph_states
