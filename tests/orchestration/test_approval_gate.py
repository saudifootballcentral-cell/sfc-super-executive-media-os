"""Tests for ApprovalGate — Package 10D."""

from __future__ import annotations

import os

import pytest

from sfc.orchestration.approval_gate import ApprovalDeniedError, ApprovalGate
from sfc.orchestration.master_state import MasterState, RunStatus, WorkflowType


class TestApprovalGateDryRun:
    def setup_method(self):
        self.gate = ApprovalGate()

    def test_dry_run_always_soft_blocks(self):
        state = MasterState(dry_run=True)
        decision = self.gate.evaluate(state)
        assert decision.approved is False
        assert decision.reason == "dry_run_mode"

    def test_dry_run_does_not_raise_on_enforce(self):
        state = MasterState(dry_run=True)
        # dry_run mode returns approved=False BUT enforce() should NOT raise
        # The caller (workflow runner) handles dry_run blocking gracefully
        decision = self.gate.evaluate(state)
        assert not decision.approved

    def test_dry_run_checks_include_governance_and_operator(self):
        state = MasterState(dry_run=True)
        decision = self.gate.evaluate(state)
        assert "governance_approved" in decision.checks
        assert "operator_approved" in decision.checks


class TestApprovalGateLiveRun:
    def setup_method(self):
        self.gate = ApprovalGate()

    def test_blocked_without_governance(self, monkeypatch):
        monkeypatch.setenv("LIVE_PUBLISHING_ENABLED", "true")
        state = MasterState(dry_run=False)
        state.approval.operator_approved = True
        decision = self.gate.evaluate(state)
        assert not decision.approved
        assert "governance_approved" in decision.reason

    def test_blocked_without_operator(self, monkeypatch):
        monkeypatch.setenv("LIVE_PUBLISHING_ENABLED", "true")
        state = MasterState(dry_run=False)
        state.approval.governance_approved = True
        decision = self.gate.evaluate(state)
        assert not decision.approved
        assert "operator_approved" in decision.reason

    def test_blocked_without_live_env(self, monkeypatch):
        monkeypatch.setenv("LIVE_PUBLISHING_ENABLED", "false")
        state = MasterState(dry_run=False)
        state.approval.governance_approved = True
        state.approval.operator_approved = True
        decision = self.gate.evaluate(state)
        assert not decision.approved

    def test_approved_with_all_three_locks(self, monkeypatch):
        monkeypatch.setenv("LIVE_PUBLISHING_ENABLED", "true")
        state = MasterState(dry_run=False)
        state.approval.governance_approved = True
        state.approval.operator_approved = True
        decision = self.gate.evaluate(state)
        assert decision.approved
        assert decision.reason == "all_checks_passed"

    def test_enforce_raises_when_blocked(self, monkeypatch):
        monkeypatch.setenv("LIVE_PUBLISHING_ENABLED", "false")
        state = MasterState(dry_run=False)
        with pytest.raises(ApprovalDeniedError):
            self.gate.enforce(state)

    def test_enforce_passes_when_all_approved(self, monkeypatch):
        monkeypatch.setenv("LIVE_PUBLISHING_ENABLED", "true")
        state = MasterState(dry_run=False)
        state.approval.governance_approved = True
        state.approval.operator_approved = True
        self.gate.enforce(state)  # should not raise


class TestGrantDenyApproval:
    def setup_method(self):
        self.gate = ApprovalGate()

    def test_grant_sets_operator_approved(self):
        state = MasterState(dry_run=False)
        self.gate.grant_operator_approval(state, granted_by="ceo")
        assert state.approval.operator_approved is True
        assert state.approval.granted_by == "ceo"

    def test_grant_sets_status_approved(self):
        state = MasterState(dry_run=False)
        self.gate.grant_operator_approval(state)
        assert state.status == RunStatus.APPROVED

    def test_deny_sets_operator_approved_false(self):
        state = MasterState(dry_run=False)
        state.approval.operator_approved = True
        self.gate.deny_operator_approval(state, denied_by="compliance")
        assert state.approval.operator_approved is False

    def test_deny_sets_status_aborted(self):
        state = MasterState(dry_run=False)
        self.gate.deny_operator_approval(state)
        assert state.status == RunStatus.ABORTED
