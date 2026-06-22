"""Tests for MasterState — Package 10D."""

from __future__ import annotations

import pytest

from sfc.orchestration.master_state import (
    ApprovalRecord,
    MasterState,
    RunStatus,
    StageRecord,
    StageStatus,
    WorkflowType,
)


class TestMasterStateDefaults:
    def test_run_id_auto_generated(self):
        s = MasterState()
        assert len(s.run_id) > 0

    def test_two_states_have_different_run_ids(self):
        s1 = MasterState()
        s2 = MasterState()
        assert s1.run_id != s2.run_id

    def test_default_status_is_pending(self):
        assert MasterState().status == RunStatus.PENDING

    def test_default_dry_run_is_true(self):
        assert MasterState().dry_run is True

    def test_default_workflow_type(self):
        assert MasterState().workflow_type == WorkflowType.FULL_PIPELINE

    def test_errors_and_warnings_start_empty(self):
        s = MasterState()
        assert s.errors == []
        assert s.warnings == []

    def test_graph_states_start_empty(self):
        assert MasterState().graph_states == {}


class TestStageTracking:
    def setup_method(self):
        self.s = MasterState()

    def test_mark_stage_started(self):
        self.s.mark_stage_started("data_ingestion")
        assert self.s.current_stage == "data_ingestion"
        assert self.s.stages["data_ingestion"].status == StageStatus.RUNNING

    def test_mark_stage_completed(self):
        self.s.mark_stage_started("data_ingestion")
        self.s.mark_stage_completed("data_ingestion")
        assert self.s.stages["data_ingestion"].status == StageStatus.COMPLETED

    def test_mark_stage_completed_sets_duration(self):
        self.s.mark_stage_started("data_ingestion")
        self.s.mark_stage_completed("data_ingestion")
        assert self.s.stages["data_ingestion"].duration_ms >= 0.0

    def test_mark_stage_failed(self):
        self.s.mark_stage_started("social_intelligence")
        self.s.mark_stage_failed("social_intelligence", "connection refused")
        assert self.s.stages["social_intelligence"].status == StageStatus.FAILED
        assert "connection refused" in self.s.errors[0]

    def test_mark_stage_skipped(self):
        self.s.mark_stage_skipped("publishing", reason="dry_run_mode")
        assert self.s.stages["publishing"].status == StageStatus.SKIPPED

    def test_completed_stages_list(self):
        self.s.mark_stage_started("data_ingestion")
        self.s.mark_stage_completed("data_ingestion")
        assert "data_ingestion" in self.s.completed_stages

    def test_failed_stages_list(self):
        self.s.mark_stage_started("publishing")
        self.s.mark_stage_failed("publishing", "fail")
        assert "publishing" in self.s.failed_stages


class TestApprovalRecord:
    def test_not_fully_approved_by_default(self):
        rec = ApprovalRecord()
        assert rec.is_fully_approved is False

    def test_fully_approved_when_both_true(self):
        rec = ApprovalRecord(governance_approved=True, operator_approved=True)
        assert rec.is_fully_approved is True

    def test_only_governance_not_enough(self):
        rec = ApprovalRecord(governance_approved=True, operator_approved=False)
        assert rec.is_fully_approved is False


class TestDecisionsAndHistory:
    def test_add_decision(self):
        s = MasterState()
        s.add_decision("governance_gate", "approved", {"count": 3})
        assert len(s.decisions) == 1
        assert s.decisions[0]["decision"] == "approved"

    def test_append_history(self):
        s = MasterState()
        s.append_history("orchestration_started")
        assert len(s.execution_history) == 1

    def test_to_summary_keys(self):
        s = MasterState()
        summary = s.to_summary()
        assert "run_id" in summary
        assert "status" in summary
        assert "dry_run" in summary
        assert "approval" in summary

    def test_total_duration_zero_before_completion(self):
        s = MasterState()
        assert s.total_duration_ms == 0.0
