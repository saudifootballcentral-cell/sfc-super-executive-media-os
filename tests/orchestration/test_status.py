"""Tests for OrchestrationStatus — Package 10D."""

from __future__ import annotations

import pytest

from sfc.orchestration.master_state import MasterState, RunStatus
from sfc.orchestration.status import OrchestrationStatus, RunSummary


class TestOrchestrationStatus:
    def setup_method(self):
        self.status = OrchestrationStatus()

    def test_active_count_zero_initially(self):
        assert self.status.active_count == 0

    def test_register_adds_to_active(self):
        s = MasterState()
        self.status.register(s)
        assert self.status.active_count == 1

    def test_complete_moves_to_history(self):
        s = MasterState()
        self.status.register(s)
        self.status.complete(s)
        assert self.status.active_count == 0
        assert self.status.total_completed == 1

    def test_get_returns_active_run(self):
        s = MasterState()
        self.status.register(s)
        found = self.status.get(s.run_id)
        assert found is s

    def test_get_returns_none_for_completed_run(self):
        s = MasterState()
        self.status.register(s)
        self.status.complete(s)
        assert self.status.get(s.run_id) is None

    def test_active_runs_returns_summaries(self):
        s = MasterState()
        self.status.register(s)
        summaries = self.status.active_runs()
        assert len(summaries) == 1
        assert isinstance(summaries[0], RunSummary)

    def test_recent_runs_limit(self):
        for _ in range(5):
            s = MasterState()
            self.status.register(s)
            self.status.complete(s)
        runs = self.status.recent_runs(limit=3)
        assert len(runs) == 3

    def test_health_returns_dict(self):
        h = self.status.health()
        assert "active_runs" in h
        assert "total_completed" in h
        assert "checked_at" in h

    def test_run_summary_is_terminal_for_completed(self):
        s = MasterState()
        s.status = RunStatus.COMPLETED
        summary = RunSummary(s)
        assert summary.is_terminal is True

    def test_run_summary_not_terminal_for_running(self):
        s = MasterState()
        s.status = RunStatus.RUNNING
        summary = RunSummary(s)
        assert summary.is_terminal is False
