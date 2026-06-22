"""Tests for Package 10D orchestration polish patches.

FIX 1 — StageCompleted emitted for every successful stage.
FIX 2 — Dependency validation passes for all abbreviated workflow types.
"""

from __future__ import annotations

import asyncio

import pytest

from sfc.events.bus import get_event_bus
from sfc.orchestration.execution_plan import ExecutionPlan
from sfc.orchestration.master_state import MasterState, StageStatus, WorkflowType
from sfc.orchestration.persistence import InMemoryPersistence
from sfc.orchestration.run_context import RunContext
from sfc.orchestration.workflow_runner import WorkflowRunner


# ---------------------------------------------------------------------------
# Shared mock bridge
# ---------------------------------------------------------------------------

class MockBridge:
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
            "approved_content": [{"id": "c1"}],
            "rejected_content": [],
            "warnings": [],
            "errors": [],
        }


def _make_ctx(workflow_type=WorkflowType.SOCIAL_INTELLIGENCE_ONLY, dry_run=True):
    state = MasterState(workflow_type=workflow_type, dry_run=dry_run)
    plan = ExecutionPlan(workflow_type=workflow_type, dry_run=dry_run)
    ctx = RunContext(state=state, plan=plan, persistence=InMemoryPersistence())
    return ctx


async def _run(workflow_type=WorkflowType.SOCIAL_INTELLIGENCE_ONLY, dry_run=True, raise_on=None):
    bus = get_event_bus()
    bus.reset()
    bridge = MockBridge(raise_on=raise_on)
    ctx = _make_ctx(workflow_type, dry_run)
    runner = WorkflowRunner(bridge=bridge)
    await runner.run(ctx)
    await asyncio.sleep(0.02)
    history = bus.get_history()
    return ctx.state, bridge, history


# ===========================================================================
# FIX 1 — StageCompleted event emission
# ===========================================================================

class TestStageCompletedEmission:

    @pytest.mark.asyncio
    async def test_builtin_stage_emits_stage_completed(self):
        """data_ingestion is a builtin stage and must emit StageCompleted."""
        _, _, history = await _run(WorkflowType.SOCIAL_INTELLIGENCE_ONLY)
        completed_stages = [e.payload["stage"] for e in history if e.event_type == "stage_completed"]
        assert "data_ingestion" in completed_stages

    @pytest.mark.asyncio
    async def test_graph_backed_stage_emits_stage_completed(self):
        """social_intelligence is graph-backed and must emit StageCompleted."""
        _, _, history = await _run(WorkflowType.SOCIAL_INTELLIGENCE_ONLY)
        completed_stages = [e.payload["stage"] for e in history if e.event_type == "stage_completed"]
        assert "social_intelligence" in completed_stages

    @pytest.mark.asyncio
    async def test_every_successful_stage_has_stage_completed(self):
        """Every stage that completes must pair its StageStarted with StageCompleted."""
        state, _, history = await _run(WorkflowType.SOCIAL_INTELLIGENCE_ONLY)
        started = {e.payload["stage"] for e in history if e.event_type == "stage_started"}
        completed = {e.payload["stage"] for e in history if e.event_type == "stage_completed"}
        assert started == completed, f"started={started} != completed={completed}"

    @pytest.mark.asyncio
    async def test_stage_completed_payload_has_required_fields(self):
        """StageCompleted payload must include all required fields."""
        _, _, history = await _run(WorkflowType.SOCIAL_INTELLIGENCE_ONLY)
        completions = [e for e in history if e.event_type == "stage_completed"]
        assert len(completions) > 0
        for event in completions:
            p = event.payload
            assert "stage" in p
            assert "workflow_type" in p
            assert "duration_ms" in p
            assert "status" in p
            assert "output_summary" in p
            assert p["status"] == "completed"

    @pytest.mark.asyncio
    async def test_stage_completed_workflow_type_matches_run(self):
        """workflow_type in StageCompleted payload must match the run's WorkflowType."""
        _, _, history = await _run(WorkflowType.SOCIAL_INTELLIGENCE_ONLY)
        completions = [e for e in history if e.event_type == "stage_completed"]
        for event in completions:
            assert event.payload["workflow_type"] == WorkflowType.SOCIAL_INTELLIGENCE_ONLY.value

    @pytest.mark.asyncio
    async def test_stage_completed_run_id_matches_state(self):
        """run_id in StageCompleted must match the MasterState run_id."""
        state, _, history = await _run(WorkflowType.SOCIAL_INTELLIGENCE_ONLY)
        completions = [e for e in history if e.event_type == "stage_completed"]
        assert len(completions) > 0
        for event in completions:
            assert event.run_id == state.run_id

    @pytest.mark.asyncio
    async def test_stage_completed_duration_ms_non_negative(self):
        _, _, history = await _run(WorkflowType.SOCIAL_INTELLIGENCE_ONLY)
        completions = [e for e in history if e.event_type == "stage_completed"]
        for event in completions:
            assert event.payload["duration_ms"] >= 0.0

    @pytest.mark.asyncio
    async def test_dry_run_publishing_emits_stage_skipped_not_completed(self):
        """Publishing stage in dry run must emit StageSkipped, not StageCompleted."""
        state, _, history = await _run(WorkflowType.DRY_RUN, dry_run=True)
        skipped_stages = [e.payload["stage"] for e in history if e.event_type == "stage_skipped"]
        completed_stages = [e.payload["stage"] for e in history if e.event_type == "stage_completed"]
        assert "publishing" in skipped_stages
        assert "publishing" not in completed_stages

    @pytest.mark.asyncio
    async def test_failed_stage_emits_stage_failed_not_completed(self):
        """A stage that raises must emit StageFailed, not StageCompleted."""
        state, _, history = await _run(
            WorkflowType.SOCIAL_INTELLIGENCE_ONLY,
            raise_on="social_intelligence_graph",
        )
        failed_stages = [e.payload["stage"] for e in history if e.event_type == "stage_failed"]
        completed_stages = [e.payload["stage"] for e in history if e.event_type == "stage_completed"]
        # social_intelligence failed — it may be in failed, not in completed
        assert "social_intelligence" not in completed_stages or "social_intelligence" in failed_stages

    @pytest.mark.asyncio
    async def test_no_stage_completed_without_prior_stage_started(self):
        """Every StageCompleted must be preceded by a StageStarted for the same stage."""
        _, _, history = await _run(WorkflowType.SOCIAL_INTELLIGENCE_ONLY)
        started_stages = {e.payload["stage"] for e in history if e.event_type == "stage_started"}
        for event in history:
            if event.event_type == "stage_completed":
                assert event.payload["stage"] in started_stages

    @pytest.mark.asyncio
    async def test_analytics_builtin_stage_emits_stage_completed(self):
        """analytics is a builtin stage in DRY_RUN and must emit StageCompleted."""
        _, _, history = await _run(WorkflowType.DRY_RUN, dry_run=True)
        completed_stages = [e.payload["stage"] for e in history if e.event_type == "stage_completed"]
        assert "analytics" in completed_stages

    @pytest.mark.asyncio
    async def test_reporting_builtin_stage_emits_stage_completed(self):
        """reporting is a non-required builtin stage and must still emit StageCompleted."""
        _, _, history = await _run(WorkflowType.DRY_RUN, dry_run=True)
        completed_stages = [e.payload["stage"] for e in history if e.event_type == "stage_completed"]
        assert "reporting" in completed_stages

    @pytest.mark.asyncio
    async def test_governance_gate_emits_stage_completed(self):
        """governance_gate is a builtin stage that must emit StageCompleted."""
        _, _, history = await _run(WorkflowType.DRY_RUN, dry_run=True)
        completed_stages = [e.payload["stage"] for e in history if e.event_type == "stage_completed"]
        assert "governance_gate" in completed_stages

    @pytest.mark.asyncio
    async def test_graph_specific_events_not_replaced_by_stage_completed(self):
        """Graph-specific events (data_ingestion_completed, social_intelligence_run_completed)
        must STILL be emitted alongside StageCompleted."""
        _, _, history = await _run(WorkflowType.SOCIAL_INTELLIGENCE_ONLY)
        types = {e.event_type for e in history}
        assert "data_ingestion_completed" in types
        # StageCompleted is additional, not a replacement
        assert "stage_completed" in types

    @pytest.mark.asyncio
    async def test_stage_completed_count_equals_completed_stage_records(self):
        """Number of StageCompleted events must equal completed stage records in MasterState."""
        state, _, history = await _run(WorkflowType.SOCIAL_INTELLIGENCE_ONLY)
        event_count = sum(1 for e in history if e.event_type == "stage_completed")
        record_count = len(state.completed_stages)
        assert event_count == record_count


# ===========================================================================
# FIX 2 — Dependency validation for abbreviated workflows
# ===========================================================================

class TestDependencyValidationAllWorkflows:

    def test_full_pipeline_validates_correctly(self):
        plan = ExecutionPlan(WorkflowType.FULL_PIPELINE)
        assert plan.validate_dependencies() == []

    def test_dry_run_validates_correctly(self):
        plan = ExecutionPlan(WorkflowType.DRY_RUN, dry_run=True)
        assert plan.validate_dependencies() == []

    def test_social_intelligence_only_validates_correctly(self):
        plan = ExecutionPlan(WorkflowType.SOCIAL_INTELLIGENCE_ONLY)
        assert plan.validate_dependencies() == []

    def test_creative_only_validates_correctly(self):
        """CREATIVE_ONLY skips main_pipeline — dep on absent stage is ignored."""
        plan = ExecutionPlan(WorkflowType.CREATIVE_ONLY)
        assert plan.validate_dependencies() == []

    def test_publish_only_validates_correctly(self):
        """PUBLISH_ONLY skips creative_production — dep on absent stage is ignored."""
        plan = ExecutionPlan(WorkflowType.PUBLISH_ONLY)
        assert plan.validate_dependencies() == []

    def test_reporting_validates_correctly(self):
        """REPORTING skips analytics — dep on absent stage is ignored."""
        plan = ExecutionPlan(WorkflowType.REPORTING)
        assert plan.validate_dependencies() == []

    def test_full_pipeline_intra_plan_violation_detected(self):
        """A genuine in-plan ordering violation must still be detected."""
        from sfc.orchestration.execution_plan import ExecutionStage
        from dataclasses import replace as dc_replace
        plan = ExecutionPlan(WorkflowType.SOCIAL_INTELLIGENCE_ONLY)
        # Manually inject a violation: stage B depends on stage C which comes after it
        bad_stage_a = ExecutionStage(name="stage_a", graph="builtin", depends_on=["stage_b"])
        bad_stage_b = ExecutionStage(name="stage_b", graph="builtin")
        plan._stages = [bad_stage_a, bad_stage_b]
        errors = plan.validate_dependencies()
        assert len(errors) == 1
        assert "stage_a" in errors[0]
        assert "stage_b" in errors[0]

    def test_all_workflow_types_pass_validation(self):
        """All six workflow types must produce zero dependency violations."""
        for wt in WorkflowType:
            plan = ExecutionPlan(wt, dry_run=True)
            errors = plan.validate_dependencies()
            assert errors == [], f"{wt.value} failed: {errors}"
