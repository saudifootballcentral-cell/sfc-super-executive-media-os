"""Tests for ExecutionPlan — Package 10D."""

from __future__ import annotations

import pytest

from sfc.orchestration.execution_plan import ExecutionPlan
from sfc.orchestration.master_state import WorkflowType


class TestExecutionPlanStages:
    def test_full_pipeline_has_expected_stages(self):
        plan = ExecutionPlan(WorkflowType.FULL_PIPELINE)
        names = plan.stage_names
        assert "data_ingestion" in names
        assert "social_intelligence" in names
        assert "main_pipeline" in names
        assert "creative_production" in names
        assert "governance_gate" in names
        assert "operator_approval" in names
        assert "publishing" in names
        assert "analytics" in names

    def test_social_only_has_fewer_stages(self):
        full = ExecutionPlan(WorkflowType.FULL_PIPELINE)
        social = ExecutionPlan(WorkflowType.SOCIAL_INTELLIGENCE_ONLY)
        assert len(social.stages) < len(full.stages)
        assert "publishing" not in social.stage_names

    def test_dry_run_has_publishing_stage(self):
        plan = ExecutionPlan(WorkflowType.DRY_RUN, dry_run=True)
        assert "publishing" in plan.stage_names

    def test_publishing_is_skippable_in_dry_run(self):
        plan = ExecutionPlan(WorkflowType.DRY_RUN, dry_run=True)
        assert plan.is_skippable("publishing") is True

    def test_publishing_not_skippable_in_live_run(self):
        plan = ExecutionPlan(WorkflowType.FULL_PIPELINE, dry_run=False)
        assert plan.is_skippable("publishing") is False

    def test_data_ingestion_not_skippable(self):
        plan = ExecutionPlan(WorkflowType.FULL_PIPELINE, dry_run=True)
        assert plan.is_skippable("data_ingestion") is False

    def test_get_stage_returns_stage(self):
        plan = ExecutionPlan(WorkflowType.FULL_PIPELINE)
        stage = plan.get_stage("governance_gate")
        assert stage is not None
        assert stage.name == "governance_gate"

    def test_get_stage_returns_none_for_unknown(self):
        plan = ExecutionPlan(WorkflowType.FULL_PIPELINE)
        assert plan.get_stage("nonexistent") is None

    def test_validate_dependencies_returns_empty_for_valid_plan(self):
        plan = ExecutionPlan(WorkflowType.FULL_PIPELINE)
        errors = plan.validate_dependencies()
        assert errors == []

    def test_to_dict_has_stages_key(self):
        plan = ExecutionPlan(WorkflowType.FULL_PIPELINE)
        d = plan.to_dict()
        assert "stages" in d
        assert len(d["stages"]) > 0

    def test_reporting_plan_stages(self):
        plan = ExecutionPlan(WorkflowType.REPORTING)
        assert "reporting" in plan.stage_names

    def test_creative_only_plan(self):
        plan = ExecutionPlan(WorkflowType.CREATIVE_ONLY)
        assert "creative_production" in plan.stage_names
        assert "governance_gate" in plan.stage_names
