"""Tests for AuditTrail — Package 10D."""

from __future__ import annotations

from sfc.orchestration.audit_trail import AuditEntry, AuditTrail


class TestAuditTrail:
    def setup_method(self):
        self.trail = AuditTrail(run_id="test-run-001")

    def test_log_returns_entry(self):
        entry = self.trail.log("data_ingestion", "cache_primed")
        assert isinstance(entry, AuditEntry)

    def test_entry_count_increases(self):
        self.trail.log("stage", "action")
        self.trail.log("stage", "action2")
        assert self.trail.entry_count == 2

    def test_log_stage_start(self):
        self.trail.log_stage_start("data_ingestion")
        entries = self.trail.entries()
        assert any("data_ingestion" in e.action for e in entries)

    def test_log_stage_complete(self):
        self.trail.log_stage_complete("data_ingestion", duration_ms=42.0)
        entries = self.trail.entries()
        assert any(e.details.get("duration_ms") == 42.0 for e in entries)

    def test_log_stage_fail_severity_is_error(self):
        self.trail.log_stage_fail("publishing", "timeout")
        errors = self.trail.entries(severity="error")
        assert len(errors) == 1
        assert "timeout" in errors[0].details["error"]

    def test_has_errors_after_failure(self):
        self.trail.log_stage_fail("publishing", "err")
        assert self.trail.has_errors is True

    def test_no_errors_initially(self):
        assert self.trail.has_errors is False

    def test_log_approval_granted(self):
        self.trail.log_approval("operator_approval", approved=True, actor="ceo")
        entries = self.trail.entries()
        assert any("approval_granted" in e.action for e in entries)

    def test_log_approval_denied(self):
        self.trail.log_approval("operator_approval", approved=False, actor="ceo")
        entries = self.trail.entries()
        assert any("approval_denied" in e.action for e in entries)

    def test_log_recovery(self):
        self.trail.log_recovery("social_intelligence", "retry", 1)
        entries = self.trail.entries(severity="warning")
        assert any("recovery_attempted" in e.action for e in entries)

    def test_to_dict_list(self):
        self.trail.log("stage", "action")
        dicts = self.trail.to_dict_list()
        assert len(dicts) == 1
        assert "entry_id" in dicts[0]
        assert "timestamp" in dicts[0]
        assert dicts[0]["run_id"] == "test-run-001"

    def test_filter_by_severity(self):
        self.trail.log("s", "a", severity="info")
        self.trail.log("s", "b", severity="warning")
        self.trail.log("s", "c", severity="error")
        assert len(self.trail.entries(severity="info")) == 1
        assert len(self.trail.entries(severity="error")) == 1
        assert len(self.trail.entries()) == 3
