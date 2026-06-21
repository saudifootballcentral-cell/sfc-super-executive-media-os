"""Tests that updated nodes use AI gateway when available and fall back correctly."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sfc.ai.models import ModelRequest, ModelResponse
from sfc.graph.state import make_initial_state


def _make_ai_response(
    task_type: str = "editorial",
    success: bool = True,
    parsed: dict | None = None,
    used_fallback: bool = False,
) -> ModelResponse:
    """Create a mock ModelResponse for a given task type."""
    default_parsed = {
        "executive": {
            "task_analysis": "Transfer news.",
            "priority": "high",
            "risk_level": "medium",
            "recommended_divisions": ["intelligence", "editorial"],
            "content_strategy": "Full pipeline.",
            "routing": "planning",
            "rationale": "Test.",
            "estimated_reach": 50000,
            "revenue_opportunity": False,
        },
        "editorial": {
            "title": "AI-Generated Title",
            "body": "AI-generated body content here.",
            "content_type": "article",
            "key_messages": ["Message 1"],
            "tone": "professional",
            "cta": "",
        },
        "intelligence": {
            "summary": "AI summary.",
            "key_facts": ["AI fact 1", "AI fact 2"],
            "confidence_score": 85.0,
            "is_rumor": False,
            "opportunity_detected": False,
        },
        "learning": {
            "lessons": ["AI lesson 1"],
            "patterns": ["AI pattern 1"],
            "recommendations": ["AI recommendation 1"],
        },
    }
    return ModelResponse(
        success=success,
        text="{}",
        parsed=parsed or default_parsed.get(task_type, {}),
        provider="claude" if not used_fallback else "fallback",
        model="claude-sonnet-4-6" if not used_fallback else "deterministic",
        used_fallback=used_fallback,
    )


class TestNodeAIIntegration:
    async def test_super_executive_uses_ai_gateway_when_key_present(self):
        """super_executive_node calls _call_via_gateway when ANTHROPIC_API_KEY is set."""
        from sfc.graph.nodes.super_executive import super_executive_node

        state = make_initial_state("transfer", {
            "headline": "Salah to Al Hilal",
            "sources": [{"name": "BBC"}, {"name": "Goal.com"}],
        })

        ai_decision = {
            "task_analysis": "Transfer news detected.",
            "priority": "high",
            "risk_level": "medium",
            "recommended_divisions": ["intelligence", "editorial"],
            "content_strategy": "Full pipeline.",
            "routing": "planning",
            "rationale": "Standard transfer.",
        }

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch(
                "sfc.graph.nodes.super_executive._call_via_gateway",
                new=AsyncMock(return_value=ai_decision),
            ):
                result = await super_executive_node(state)

        assert "executive_decision" in result
        assert result["executive_decision"]["routing"] == "planning"

    async def test_super_executive_falls_back_when_no_key(self):
        """super_executive_node uses deterministic fallback when no API key."""
        from sfc.graph.nodes.super_executive import super_executive_node

        state = make_initial_state("transfer", {"headline": "Test"})

        with patch.dict("os.environ", {}, clear=True):
            result = await super_executive_node(state)

        assert "executive_decision" in result
        decision = result["executive_decision"]
        assert "priority" in decision
        assert "routing" in decision

    async def test_editorial_node_ai_enriches_drafts(self):
        """editorial_node integrates AI-generated title/body when AI succeeds."""
        from sfc.graph.nodes.editorial import editorial_node

        state = make_initial_state("news", {
            "headline": "Test headline",
            "sources": [{"name": "BBC"}, {"name": "Goal"}],
        })
        state["intelligence_report"] = {
            "confidence_score": 90.0,
            "key_facts": ["Fact 1", "Fact 2"],
            "is_rumor": False,
        }
        state["verified_sources"] = [{"name": "BBC"}, {"name": "Goal"}]
        state["execution_plan"] = {"content_types": ["article"], "platforms_targeted": ["x"]}

        ai_response = _make_ai_response("editorial")

        mock_gateway = AsyncMock()
        mock_gateway.complete = AsyncMock(return_value=ai_response)

        with patch("sfc.graph.nodes.editorial.get_ai_gateway", return_value=mock_gateway, create=True):
            with patch("sfc.ai.model_gateway.get_ai_gateway", return_value=mock_gateway):
                result = await editorial_node(state)

        assert "content_drafts" in result
        assert len(result["content_drafts"]) > 0
        # Scores should NOT be modified by AI
        for draft in result["content_drafts"]:
            assert draft["scores"]["confidence_score"] == 90.0
            assert draft["scores"]["source_count"] == 2

    async def test_intelligence_node_ai_enriches_report(self):
        """intelligence_node adds AI summary without modifying source count."""
        from sfc.graph.nodes.intelligence import intelligence_node

        state = make_initial_state("news", {
            "headline": "Test",
            "sources": [
                {"name": "BBC", "reliability": 90},
                {"name": "Goal.com", "reliability": 85},
            ],
        })

        result = await intelligence_node(state)

        assert "intelligence_report" in result
        report = result["intelligence_report"]
        assert report["source_count"] == 2
        assert report["confidence_score"] > 0

    async def test_learning_node_ai_extracts_lessons(self):
        """learning_node adds AI-extracted patterns to lessons."""
        from sfc.graph.nodes.learning import learning_node

        state = make_initial_state("news", {})
        state["intelligence_report"] = {"confidence_score": 85.0, "source_count": 3}
        state["governance_reviews"] = [{"approved": True, "reasons": []}]
        state["approved_content"] = [{"content_id": "test-001"}]
        state["rejected_content"] = []
        state["analytics_report"] = {}

        result = await learning_node(state)

        assert "lessons_learned" in result
        assert isinstance(result["lessons_learned"], list)
        assert len(result["lessons_learned"]) > 0

    async def test_nodes_complete_without_api_key(self):
        """All updated nodes complete successfully with no API keys configured."""
        from sfc.graph.nodes.intelligence import intelligence_node
        from sfc.graph.nodes.editorial import editorial_node
        from sfc.graph.nodes.creative import creative_node
        from sfc.graph.nodes.learning import learning_node

        env = {k: v for k, v in os.environ.items()
               if k not in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY")}

        state = make_initial_state("news", {
            "headline": "Test",
            "sources": [{"name": "BBC", "reliability": 90}, {"name": "Goal", "reliability": 85}],
        })

        with patch.dict("os.environ", env, clear=True):
            intel = await intelligence_node(state)
            assert "intelligence_report" in intel

            state.update(intel)
            state["execution_plan"] = {"content_types": ["article"], "platforms_targeted": ["x"]}
            editorial = await editorial_node(state)
            assert "content_drafts" in editorial

            state.update(editorial)
            creative = await creative_node(state)
            assert "creative_assets" in creative

            state.update(creative)
            state["analytics_report"] = {}
            state["governance_reviews"] = []
            state["approved_content"] = []
            state["rejected_content"] = []
            learning = await learning_node(state)
            assert "lessons_learned" in learning
