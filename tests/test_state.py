"""Tests for SFCState initialization, defaults, and reducer behaviour."""

import operator
import pytest

from sfc.graph.state import SFCState, make_initial_state


class TestMakeInitialState:
    def test_returns_dict(self):
        state = make_initial_state("transfer_news", {"headline": "test"})
        assert isinstance(state, dict)

    def test_task_type_preserved(self):
        state = make_initial_state("transfer_news", {"foo": "bar"})
        assert state["task_type"] == "transfer_news"

    def test_task_payload_preserved(self):
        payload = {"headline": "Salah to Al Hilal", "sources": 3}
        state = make_initial_state("transfer_news", payload)
        assert state["task_payload"] == payload

    def test_run_id_generated_when_not_provided(self):
        state = make_initial_state("transfer_news", {})
        assert isinstance(state["run_id"], str)
        assert len(state["run_id"]) > 8

    def test_run_id_can_be_forced(self):
        state = make_initial_state("transfer_news", {}, run_id="fixed-id-001")
        assert state["run_id"] == "fixed-id-001"

    def test_started_at_is_iso_string(self):
        import datetime
        state = make_initial_state("transfer_news", {})
        dt = datetime.datetime.fromisoformat(state["started_at"])
        assert dt.year >= 2024

    def test_completed_at_is_none_initially(self):
        state = make_initial_state("transfer_news", {})
        assert state["completed_at"] is None

    def test_list_fields_are_empty(self):
        state = make_initial_state("transfer_news", {})
        for field in [
            "verified_sources", "revenue_signals", "content_drafts",
            "creative_assets", "governance_reviews", "approved_content",
            "rejected_content", "publish_queue", "lessons_learned",
            "memory_update_log", "errors", "warnings",
        ]:
            assert state[field] == [], f"{field} should be empty list"

    def test_dict_fields_are_empty(self):
        state = make_initial_state("transfer_news", {})
        for field in [
            "executive_decision", "execution_plan",
            "intelligence_report", "analytics_background_data",
            "publish_results", "analytics_report",
        ]:
            assert state[field] == {}, f"{field} should be empty dict"

    def test_pipeline_stage_is_initial(self):
        state = make_initial_state("match_report", {})
        assert state["pipeline_stage"] == "init"

    def test_two_states_have_unique_run_ids(self):
        s1 = make_initial_state("transfer_news", {})
        s2 = make_initial_state("transfer_news", {})
        assert s1["run_id"] != s2["run_id"]


class TestStateReducers:
    """Errors and warnings use operator.add so parallel writes merge safely."""

    def test_errors_reducer_merges(self):
        # Simulate what LangGraph does when two parallel nodes return errors
        base = []
        result = operator.add(base, ["error A"])
        result = operator.add(result, ["error B"])
        assert result == ["error A", "error B"]

    def test_warnings_reducer_merges(self):
        base = ["warn 0"]
        result = operator.add(base, ["warn 1", "warn 2"])
        assert result == ["warn 0", "warn 1", "warn 2"]

    def test_empty_add_is_noop(self):
        existing = ["existing error"]
        result = operator.add(existing, [])
        assert result == ["existing error"]
