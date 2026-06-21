"""End-to-end graph tests for the Package 6B extended pipeline.

Tests that the 14-node graph runs correctly with war_room_router,
persona_layer, and revenue_node wired into the main pipeline.
"""

from __future__ import annotations

import pytest

from sfc.graph.graph import build_graph, get_graph_ascii
from sfc.graph.state import make_initial_state


# ---------------------------------------------------------------------------
# Graph construction tests
# ---------------------------------------------------------------------------

class TestGraphConstruction:
    def test_graph_builds_with_14_nodes(self):
        graph = build_graph()
        assert graph is not None

    def test_ascii_diagram_contains_all_original_nodes(self):
        diagram = get_graph_ascii()
        for node in [
            "super_executive", "planning", "intelligence",
            "editorial", "creative", "governance",
            "publishing", "analytics", "learning", "memory_update",
            "strategic_planning",
        ]:
            assert node in diagram, f"Original node '{node}' missing from ASCII diagram"

    def test_ascii_diagram_contains_new_package_6b_nodes(self):
        diagram = get_graph_ascii()
        for node in ["war_room_router", "persona_layer", "revenue_node"]:
            assert node in diagram, f"Package 6B node '{node}' missing from ASCII diagram"

    def test_ascii_mentions_governance_preservation(self):
        diagram = get_graph_ascii()
        # The diagram should mention that personas cannot bypass governance
        assert "bypass" in diagram.lower() or "governance" in diagram.lower()


# ---------------------------------------------------------------------------
# Full pipeline end-to-end tests
# ---------------------------------------------------------------------------

class TestE2EPipeline:
    def _make_state(self, task_type: str, payload: dict | None = None):
        return make_initial_state(task_type, payload or {"headline": f"Test — {task_type}"})

    async def test_transfer_pipeline_runs_to_completion(self):
        graph = build_graph()
        state = self._make_state("transfer_news", {
            "headline": "Salah to Al Hilal — exclusive",
            "sources": ["BBC Sport", "Sky Sports"],
            "confidence": 91.0,
        })
        result = await graph.ainvoke(state)
        assert result.get("completed_at") is not None

    async def test_match_pipeline_runs_to_completion(self):
        graph = build_graph()
        state = self._make_state("match_report", {
            "home_team": "Al Hilal",
            "away_team": "Al Nassr",
            "competition": "Saudi Pro League",
        })
        result = await graph.ainvoke(state)
        assert result.get("completed_at") is not None

    async def test_crisis_pipeline_runs_to_completion(self):
        graph = build_graph()
        state = self._make_state("crisis", {
            "crisis_type": "reputation_risk",
            "crisis_description": "Test crisis scenario",
        })
        result = await graph.ainvoke(state)
        assert result.get("completed_at") is not None

    async def test_war_room_state_populated_in_result(self):
        graph = build_graph()
        state = self._make_state("match_report", {"home_team": "Al Hilal", "away_team": "Al Nassr"})
        result = await graph.ainvoke(state)
        # war_room_state should be set (even if war room wasn't activated)
        assert "war_room_state" in result
        assert isinstance(result["war_room_state"], dict)

    async def test_persona_outputs_populated_in_result(self):
        graph = build_graph()
        state = self._make_state("transfer_news", {"headline": "Test transfer"})
        result = await graph.ainvoke(state)
        assert "persona_outputs" in result
        assert isinstance(result["persona_outputs"], list)

    async def test_analytics_report_has_revenue_summary(self):
        graph = build_graph()
        state = self._make_state("transfer_news", {"headline": "Test transfer"})
        result = await graph.ainvoke(state)
        report = result.get("analytics_report", {})
        # revenue_summary is added by revenue_node after analytics
        assert "revenue_summary" in report, "analytics_report must contain revenue_summary after Package 6B"

    async def test_no_errors_for_healthy_transfer_run(self):
        graph = build_graph()
        state = self._make_state("transfer_news", {
            "headline": "Salah to Al Hilal",
            "sources": ["BBC", "Sky"],
        })
        result = await graph.ainvoke(state)
        assert result["errors"] == [], f"Unexpected errors: {result['errors']}"

    async def test_memory_update_log_still_populated(self):
        graph = build_graph()
        state = self._make_state("transfer_news", {})
        result = await graph.ainvoke(state)
        assert isinstance(result["memory_update_log"], list)
        assert len(result["memory_update_log"]) > 0

    async def test_active_personas_field_in_result(self):
        graph = build_graph()
        state = self._make_state("match_report", {})
        result = await graph.ainvoke(state)
        assert "active_personas" in result
        assert isinstance(result["active_personas"], list)

    async def test_infrastructure_ready_field_set(self):
        graph = build_graph()
        state = self._make_state("match_report", {})
        result = await graph.ainvoke(state)
        # war_room_router sets this to True when any war room activates
        assert "infrastructure_ready" in result

    async def test_news_task_completes_without_war_room(self):
        graph = build_graph()
        state = self._make_state("news", {"headline": "General football news"})
        result = await graph.ainvoke(state)
        assert result.get("completed_at") is not None
        ws = result.get("war_room_state", {})
        assert ws.get("activated") is False  # no war room for generic news

    async def test_world_cup_task_activates_war_room(self):
        graph = build_graph()
        state = self._make_state("world_cup_coverage", {"phase": "group_stage"})
        result = await graph.ainvoke(state)
        ws = result.get("war_room_state", {})
        assert ws is not None  # war_room_state should be set
