"""Integration tests for the revenue_node (Package 6B).

Tests that revenue_node correctly processes revenue_signals and enriches
the analytics_report with a structured revenue_summary.
"""

from __future__ import annotations

import pytest

from sfc.graph.nodes.revenue_node import revenue_node
from sfc.graph.state import make_initial_state


# ---------------------------------------------------------------------------
# Helper builders
# ---------------------------------------------------------------------------

def _state_with_signals(task_type: str = "transfer", signals: list | None = None):
    state = make_initial_state(task_type, {})
    state["revenue_signals"] = signals if signals is not None else [
        {
            "brand": "STC Sport",
            "category": "telecom",
            "estimated_value_usd": 18_000,
            "activation_type": "sponsored_content",
            "platforms": ["tiktok", "instagram_reels"],
            "status": "opportunity",
        },
        {
            "brand": "Al Rajhi Bank",
            "category": "finance",
            "estimated_value_usd": 12_000,
            "activation_type": "sponsored_content",
            "platforms": ["youtube"],
            "status": "opportunity",
        },
    ]
    state["analytics_report"] = {
        "run_id": "test-run-001",
        "content_pieces_published": 2,
        "estimated_reach": 100_000,
    }
    return state


# ---------------------------------------------------------------------------
# Revenue node tests
# ---------------------------------------------------------------------------

class TestRevenueNode:
    async def test_node_enriches_analytics_report(self):
        state = _state_with_signals()
        result = await revenue_node(state)
        assert "analytics_report" in result
        report = result["analytics_report"]
        assert "revenue_summary" in report, "analytics_report must contain revenue_summary"

    async def test_revenue_summary_has_required_keys(self):
        state = _state_with_signals()
        result = await revenue_node(state)
        summary = result["analytics_report"]["revenue_summary"]
        for key in ["total_opportunity_usd", "signal_count", "high_value_signals",
                    "priority_brand", "activation_ready", "processed_at"]:
            assert key in summary, f"Missing key '{key}' in revenue_summary"

    async def test_total_opportunity_calculated_correctly(self):
        state = _state_with_signals()
        result = await revenue_node(state)
        total = result["analytics_report"]["revenue_summary"]["total_opportunity_usd"]
        assert total == 30_000  # 18_000 + 12_000

    async def test_signal_count_matches_input(self):
        state = _state_with_signals()
        result = await revenue_node(state)
        count = result["analytics_report"]["revenue_summary"]["signal_count"]
        assert count == 2

    async def test_high_value_signals_above_threshold(self):
        state = _state_with_signals()
        result = await revenue_node(state)
        high_value = result["analytics_report"]["revenue_summary"]["high_value_signals"]
        assert high_value == 2  # Both $18k and $12k exceed $10k threshold

    async def test_priority_brand_is_highest_value(self):
        state = _state_with_signals()
        result = await revenue_node(state)
        priority = result["analytics_report"]["revenue_summary"]["priority_brand"]
        assert priority == "STC Sport"  # $18k > $12k

    async def test_empty_signals_produce_zero_summary(self):
        state = _state_with_signals(signals=[])
        result = await revenue_node(state)
        summary = result["analytics_report"]["revenue_summary"]
        assert summary["total_opportunity_usd"] == 0
        assert summary["signal_count"] == 0
        assert summary["activation_ready"] is False
        assert summary["priority_brand"] is None

    async def test_node_preserves_existing_analytics_fields(self):
        state = _state_with_signals()
        result = await revenue_node(state)
        report = result["analytics_report"]
        assert report.get("run_id") == "test-run-001"
        assert report.get("content_pieces_published") == 2
        assert report.get("estimated_reach") == 100_000

    async def test_node_returns_pipeline_stage(self):
        state = _state_with_signals()
        result = await revenue_node(state)
        assert result.get("pipeline_stage") == "revenue_processed"

    async def test_node_never_raises_exception(self):
        state = make_initial_state("news", {})
        try:
            result = await revenue_node(state)
            assert result is not None
        except Exception as exc:
            pytest.fail(f"revenue_node raised: {exc}")

    async def test_single_high_value_signal_activates_flag(self):
        state = _state_with_signals(signals=[
            {"brand": "adidas", "category": "sportswear", "estimated_value_usd": 50_000,
             "activation_type": "sponsored_content"}
        ])
        result = await revenue_node(state)
        summary = result["analytics_report"]["revenue_summary"]
        assert summary["activation_ready"] is True

    async def test_low_value_signal_does_not_activate_flag(self):
        state = _state_with_signals(signals=[
            {"brand": "Small Brand", "category": "local", "estimated_value_usd": 500,
             "activation_type": "ad_revenue"}
        ])
        result = await revenue_node(state)
        summary = result["analytics_report"]["revenue_summary"]
        assert summary["activation_ready"] is False  # Below $10k threshold

    async def test_sponsor_categories_listed(self):
        state = _state_with_signals()
        result = await revenue_node(state)
        categories = result["analytics_report"]["revenue_summary"].get("sponsor_categories", [])
        assert "telecom" in categories
        assert "finance" in categories
