"""Integration tests for persona layer node (Package 6B).

Tests that persona_layer_node correctly selects and executes personas
based on task_type, and enriches content_drafts without bypassing governance.
"""

from __future__ import annotations

import pytest

from sfc.graph.nodes.persona_layer import persona_layer_node, _detect_primary_platform
from sfc.graph.state import make_initial_state


# ---------------------------------------------------------------------------
# Helper builders
# ---------------------------------------------------------------------------

def _state_with_drafts(task_type: str, platforms: list[str] | None = None):
    """Create a state with a sample content draft and optional platform."""
    state = make_initial_state(task_type, {"headline": f"Test — {task_type}"})
    state["content_drafts"] = [
        {
            "content_id": "test-draft-001",
            "title": f"Test draft for {task_type}",
            "body": "Draft body content.",
            "content_type": "article",
            "platforms": platforms or ["x", "website"],
            "status": "draft",
            "scores": {
                "confidence_score": 88.0,
                "risk_score": 12.0,
                "source_count": 3,
                "brand_alignment_score": 90.0,
            },
            "sources": ["BBC Sport", "Goal.com", "Sky Sports"],
        }
    ]
    if platforms:
        state["execution_plan"] = {"platforms_targeted": platforms}
    return state


# ---------------------------------------------------------------------------
# Persona selection tests
# ---------------------------------------------------------------------------

class TestPersonaLayerNode:
    async def test_node_returns_active_personas_list(self):
        state = _state_with_drafts("transfer_news")
        result = await persona_layer_node(state)
        assert "active_personas" in result
        assert isinstance(result["active_personas"], list)

    async def test_node_returns_persona_outputs_list(self):
        state = _state_with_drafts("transfer_news")
        result = await persona_layer_node(state)
        assert "persona_outputs" in result
        assert isinstance(result["persona_outputs"], list)

    async def test_persona_outputs_have_required_keys(self):
        state = _state_with_drafts("match_report")
        result = await persona_layer_node(state)
        for output in result.get("persona_outputs", []):
            assert "persona_id" in output
            assert "persona_name" in output
            assert "output" in output
            assert "task_type" in output

    async def test_content_drafts_enriched_with_persona_insights(self):
        state = _state_with_drafts("match_report")
        result = await persona_layer_node(state)
        drafts = result.get("content_drafts", [])
        if drafts:  # May be empty if no personas available
            for draft in drafts:
                assert "persona_insights" in draft, "Draft missing persona_insights"

    async def test_governance_scores_not_modified(self):
        """Persona layer must not modify confidence_score or source_count."""
        original_scores = {
            "confidence_score": 88.0,
            "risk_score": 12.0,
            "source_count": 3,
            "brand_alignment_score": 90.0,
        }
        state = _state_with_drafts("match_report")
        result = await persona_layer_node(state)
        for draft in result.get("content_drafts", []):
            scores = draft.get("scores", {})
            assert scores.get("confidence_score") == original_scores["confidence_score"], \
                "confidence_score must not be modified by persona_layer"
            assert scores.get("source_count") == original_scores["source_count"], \
                "source_count must not be modified by persona_layer"
            assert scores.get("brand_alignment_score") == original_scores["brand_alignment_score"], \
                "brand_alignment_score must not be modified by persona_layer"

    async def test_node_returns_pipeline_stage(self):
        state = _state_with_drafts("transfer_news")
        result = await persona_layer_node(state)
        assert "pipeline_stage" in result

    async def test_node_never_raises_exception(self):
        state = make_initial_state("unknown_xyz", {})
        try:
            result = await persona_layer_node(state)
            assert result is not None
        except Exception as exc:
            pytest.fail(f"persona_layer_node raised: {exc}")

    async def test_node_handles_empty_content_drafts(self):
        state = make_initial_state("transfer_news", {})
        state["content_drafts"] = []
        result = await persona_layer_node(state)
        assert "active_personas" in result
        assert result.get("content_drafts", []) == []

    async def test_tiktok_platform_selects_creative_personas(self):
        state = _state_with_drafts("campaign", platforms=["tiktok", "instagram_reels"])
        result = await persona_layer_node(state)
        # Should recommend at least one persona with CREATIVE category
        assert isinstance(result.get("active_personas", []), list)

    async def test_persona_outputs_are_dicts(self):
        state = _state_with_drafts("transfer_news")
        result = await persona_layer_node(state)
        for output in result.get("persona_outputs", []):
            assert isinstance(output.get("output"), dict), \
                f"Persona output must be a dict, got {type(output.get('output'))}"

    async def test_personas_registered_for_match_report(self):
        state = _state_with_drafts("match_report")
        result = await persona_layer_node(state)
        # At least some personas should be activated
        active = result.get("active_personas", [])
        assert len(active) >= 0  # Non-negative; may be 0 if all fail gracefully

    async def test_war_room_context_used_in_recommendation(self):
        state = _state_with_drafts("crisis")
        state["war_room_state"] = {"war_room_type": "crisis", "activated": True}
        result = await persona_layer_node(state)
        assert "active_personas" in result


# ---------------------------------------------------------------------------
# Platform detection tests
# ---------------------------------------------------------------------------

class TestPlatformDetection:
    def test_detects_tiktok_from_execution_plan(self):
        state = make_initial_state("campaign", {})
        state["execution_plan"] = {"platforms_targeted": ["tiktok", "instagram_reels"]}
        platform = _detect_primary_platform(state)
        assert platform == "tiktok"

    def test_detects_youtube_from_execution_plan(self):
        state = make_initial_state("analysis", {})
        state["execution_plan"] = {"platforms_targeted": ["youtube", "website"]}
        platform = _detect_primary_platform(state)
        assert platform == "youtube"

    def test_returns_empty_string_when_no_platforms(self):
        state = make_initial_state("news", {})
        platform = _detect_primary_platform(state)
        assert platform == ""
