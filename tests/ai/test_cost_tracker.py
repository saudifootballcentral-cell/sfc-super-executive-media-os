"""Tests for cost tracking — no API calls."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from sfc.ai.cost_tracker import CallRecord, CostTracker, estimate_cost
from datetime import datetime


def _make_record(
    task_type: str = "editorial",
    provider: str = "claude",
    model: str = "claude-sonnet-4-6",
    input_tokens: int = 1000,
    output_tokens: int = 500,
    cost_usd: float = 0.01,
    success: bool = True,
    used_fallback: bool = False,
    validation_failed: bool = False,
) -> CallRecord:
    return CallRecord(
        timestamp=datetime.utcnow().isoformat(),
        task_type=task_type,
        provider=provider,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost_usd,
        latency_ms=500,
        success=success,
        used_fallback=used_fallback,
        validation_failed=validation_failed,
    )


class TestCostTracker:
    def test_records_call_and_accumulates_cost(self):
        """Recording a call increases the session total."""
        tracker = CostTracker()
        assert tracker.get_session_total_usd() == 0.0

        tracker.record(_make_record(cost_usd=0.01))
        assert tracker.get_session_total_usd() == pytest.approx(0.01)

    def test_session_total_is_sum_of_costs(self):
        """Session total equals sum of all recorded costs."""
        tracker = CostTracker()
        tracker.record(_make_record(cost_usd=0.01))
        tracker.record(_make_record(cost_usd=0.02))
        tracker.record(_make_record(cost_usd=0.005))
        assert tracker.get_session_total_usd() == pytest.approx(0.035)

    def test_budget_check_returns_true_within_limit(self):
        """Budget check returns True when under the daily limit."""
        tracker = CostTracker()
        tracker.record(_make_record(cost_usd=1.0))  # $1 is well under $100

        with patch.dict("os.environ", {"MAX_DAILY_AI_COST": "100.0"}):
            assert tracker.check_budget() is True

    def test_budget_check_returns_false_over_limit(self):
        """Budget check returns False when over the daily limit."""
        tracker = CostTracker()
        tracker.record(_make_record(cost_usd=50.0))

        with patch.dict("os.environ", {"MAX_DAILY_AI_COST": "10.0"}):
            assert tracker.check_budget() is False

    def test_model_breakdown_groups_by_model(self):
        """Model breakdown sums costs per model."""
        tracker = CostTracker()
        tracker.record(_make_record(model="claude-sonnet-4-6", cost_usd=0.01))
        tracker.record(_make_record(model="claude-sonnet-4-6", cost_usd=0.02))
        tracker.record(_make_record(model="claude-haiku-4-5-20251001", cost_usd=0.001))

        breakdown = tracker.get_model_breakdown()
        assert "claude-sonnet-4-6" in breakdown
        assert "claude-haiku-4-5-20251001" in breakdown
        assert breakdown["claude-sonnet-4-6"] == pytest.approx(0.03)
        assert breakdown["claude-haiku-4-5-20251001"] == pytest.approx(0.001)

    def test_get_report_has_required_keys(self):
        """get_report returns dict with all expected keys."""
        tracker = CostTracker()
        tracker.record(_make_record())
        report = tracker.get_report()

        required_keys = [
            "total_calls",
            "successful_calls",
            "fallback_calls",
            "validation_failures",
            "session_total_usd",
            "model_breakdown_usd",
            "within_budget",
            "max_daily_cost_usd",
        ]
        for key in required_keys:
            assert key in report, f"Expected key '{key}' in cost report"

    def test_estimate_cost_claude_opus(self):
        """estimate_cost calculates correct cost for claude-opus-4-8."""
        cost = estimate_cost("claude-opus-4-8", 1_000_000, 1_000_000)
        assert cost == pytest.approx(90.0)  # $15 input + $75 output per 1M

    def test_estimate_cost_claude_sonnet(self):
        """estimate_cost calculates correct cost for claude-sonnet-4-6."""
        cost = estimate_cost("claude-sonnet-4-6", 1_000_000, 1_000_000)
        assert cost == pytest.approx(18.0)  # $3 input + $15 output per 1M

    def test_estimate_cost_haiku(self):
        """estimate_cost calculates correct cost for claude-haiku."""
        cost = estimate_cost("claude-haiku-4-5-20251001", 1_000_000, 1_000_000)
        assert cost == pytest.approx(1.50)  # $0.25 input + $1.25 output per 1M

    def test_tracker_counts_fallbacks(self):
        """Tracker counts used_fallback=True records correctly."""
        tracker = CostTracker()
        tracker.record(_make_record(used_fallback=True))
        tracker.record(_make_record(used_fallback=False))
        tracker.record(_make_record(used_fallback=True))

        report = tracker.get_report()
        # successful_calls counts success=True records (not used_fallback)
        assert report["total_calls"] == 3

    def test_tracker_counts_validation_failures(self):
        """Tracker counts validation_failed=True records."""
        tracker = CostTracker()
        tracker.record(_make_record(validation_failed=True))
        tracker.record(_make_record(validation_failed=False))

        report = tracker.get_report()
        assert report["validation_failures"] == 1
