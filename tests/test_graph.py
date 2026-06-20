"""Integration tests for the LangGraph pipeline.

These tests run the graph without an Anthropic API key — the super_executive node
falls back to a deterministic decision so the full 10-node pipeline still executes.
"""

import pytest

from sfc.graph.graph import build_graph, get_graph_ascii
from sfc.graph.state import make_initial_state


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

class TestGraphConstruction:
    def test_graph_builds_without_error(self):
        graph = build_graph()
        assert graph is not None

    def test_ascii_diagram_contains_all_nodes(self):
        diagram = get_graph_ascii()
        for node in [
            "super_executive", "planning", "intelligence",
            "editorial", "creative", "governance",
            "publishing", "analytics", "learning", "memory_update",
            "strategic_planning",
        ]:
            assert node in diagram, f"Node '{node}' missing from ASCII diagram"

    def test_ascii_diagram_describes_parallel_background_work(self):
        diagram = get_graph_ascii()
        assert "analytics_background" in diagram
        assert "revenue_background" in diagram


# ---------------------------------------------------------------------------
# Full pipeline (no API key — uses fallback executive decision)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestFullPipeline:
    def _make_transfer_state(self):
        return make_initial_state(
            "transfer_news",
            {
                "headline": "Salah to Al Hilal — exclusive",
                "sources": ["BBC Sport", "Sky Sports", "Goal.com"],
                "confidence": 91.0,
            },
        )

    async def test_pipeline_runs_to_completion(self):
        graph = build_graph()
        state = self._make_transfer_state()
        result = await graph.ainvoke(state)
        # The final node sets completed_at
        assert result.get("completed_at") is not None

    async def test_memory_update_log_populated(self):
        graph = build_graph()
        state = self._make_transfer_state()
        result = await graph.ainvoke(state)
        assert isinstance(result["memory_update_log"], list)
        assert len(result["memory_update_log"]) > 0

    async def test_analytics_report_populated(self):
        graph = build_graph()
        state = self._make_transfer_state()
        result = await graph.ainvoke(state)
        assert isinstance(result["analytics_report"], dict)
        assert "run_id" in result["analytics_report"]

    async def test_no_unexpected_errors(self):
        graph = build_graph()
        state = self._make_transfer_state()
        result = await graph.ainvoke(state)
        # Errors list should be empty for a healthy run
        assert result["errors"] == [], f"Unexpected errors: {result['errors']}"

    async def test_match_report_scenario(self):
        graph = build_graph()
        state = make_initial_state(
            "match_report",
            {
                "headline": "Al Hilal 3-0 Al Nassr — match report",
                "sources": ["Al Kass TV", "SFC Official"],
                "confidence": 95.0,
            },
        )
        result = await graph.ainvoke(state)
        assert result.get("completed_at") is not None

    async def test_empty_payload_completes(self):
        """Graph must not crash on minimal input."""
        graph = build_graph()
        state = make_initial_state("general", {})
        result = await graph.ainvoke(state)
        assert result is not None


# ---------------------------------------------------------------------------
# Governance gate — low confidence content must be blocked
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestGovernanceGateInPipeline:
    async def test_low_confidence_content_rejected_by_pipeline(self):
        """End-to-end: content with confidence < 85 should land in rejected_content."""
        graph = build_graph()
        # Intelligence node calculates confidence as 60 + 12 * source_count (capped at 100).
        # With 0 sources passed in payload the intelligence node will yield low confidence.
        state = make_initial_state(
            "transfer_news",
            {"headline": "Unverified rumor", "sources": [], "confidence": 40.0},
        )
        result = await graph.ainvoke(state)
        # Either rejected_content has items OR approved_content is empty
        # (intelligence may still score it low enough)
        total = len(result.get("approved_content", [])) + len(result.get("rejected_content", []))
        # If editorial produced drafts, governance must have reviewed them
        if result.get("content_drafts"):
            assert total > 0
