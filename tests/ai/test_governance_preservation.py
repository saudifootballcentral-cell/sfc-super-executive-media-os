"""Tests verifying AI never bypasses constitutional governance rules."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from sfc.ai.models import ModelResponse
from sfc.graph.nodes.governance import governance_node
from sfc.graph.state import make_initial_state


def _draft_with_scores(
    confidence: float = 90.0,
    source_count: int = 3,
    brand_alignment: float = 85.0,
    risk_score: float = 10.0,
    is_rumor: bool = False,
) -> dict:
    return {
        "content_id": "test-ai-governance-001",
        "title": "AI Governance Test",
        "body": "Test content body.",
        "content_type": "article",
        "platforms": ["x"],
        "status": "draft",
        "scores": {
            "confidence_score": confidence,
            "risk_score": risk_score,
            "source_count": source_count,
            "brand_alignment_score": brand_alignment,
        },
        "sources": [f"source-{i}" for i in range(source_count)],
        "is_rumor": is_rumor,
    }


def _fake_ai_approval_response() -> ModelResponse:
    """Simulate an AI response that tries to approve content."""
    return ModelResponse(
        success=True,
        text='{"approved": true, "decision": "approve", "override": true}',
        parsed={"approved": True, "decision": "approve", "override": True},
        provider="claude",
        model="claude-sonnet-4-6",
        used_fallback=False,
    )


class TestGovernancePreservation:
    async def test_ai_cannot_approve_low_confidence_content(self):
        """Even if AI returns approval signals, low-confidence content is rejected."""
        state = make_initial_state("news", {})
        state["content_drafts"] = [_draft_with_scores(confidence=70.0)]  # Below 85 threshold

        # Mock AI to return a "approve everything" response
        mock_gateway = AsyncMock()
        mock_gateway.complete = AsyncMock(return_value=_fake_ai_approval_response())

        with patch("sfc.graph.nodes.governance.get_ai_gateway", return_value=mock_gateway, create=True):
            result = await governance_node(state)

        # Constitutional check must still reject it
        assert len(result.get("rejected_content", [])) > 0, \
            "Low-confidence content must be rejected regardless of AI output"
        assert len(result.get("approved_content", [])) == 0, \
            "AI must not approve low-confidence content"

    async def test_ai_cannot_approve_single_source_content(self):
        """Single-source content is rejected even if AI tries to approve it."""
        state = make_initial_state("news", {})
        state["content_drafts"] = [_draft_with_scores(source_count=1)]  # Below min 2

        mock_gateway = AsyncMock()
        mock_gateway.complete = AsyncMock(return_value=_fake_ai_approval_response())

        with patch("sfc.graph.nodes.governance.get_ai_gateway", return_value=mock_gateway, create=True):
            result = await governance_node(state)

        assert len(result.get("rejected_content", [])) > 0, \
            "Single-source content must be rejected regardless of AI output"

    async def test_ai_output_in_governance_is_explanatory_only(self):
        """Governance node returns reviews based on code check, not AI decisions."""
        state = make_initial_state("news", {})
        state["content_drafts"] = [_draft_with_scores(confidence=70.0)]

        result = await governance_node(state)

        # The governance_reviews must exist and be based on code check
        reviews = result.get("governance_reviews", [])
        assert len(reviews) > 0

        # Reviews should have the 'approved' field determined by code, not AI
        for review in reviews:
            assert "approved" in review
            # Low confidence = False
            assert review["approved"] is False

    async def test_constitutional_check_runs_regardless_of_ai(self):
        """Constitutional compliance check runs even when AI gateway is disabled."""
        state = make_initial_state("news", {})
        state["content_drafts"] = [_draft_with_scores(confidence=90.0, source_count=3)]

        # Make AI gateway raise an exception
        mock_gateway = AsyncMock()
        mock_gateway.complete = AsyncMock(side_effect=RuntimeError("AI is down"))

        with patch("sfc.graph.nodes.governance.get_ai_gateway", return_value=mock_gateway, create=True):
            result = await governance_node(state)

        # Should still produce governance reviews via code check
        assert "governance_reviews" in result
        assert len(result["governance_reviews"]) > 0

    async def test_ai_governance_failure_falls_back_to_code_check(self):
        """When AI fails in governance, code check results are still returned."""
        state = make_initial_state("news", {})
        state["content_drafts"] = [_draft_with_scores(confidence=90.0, source_count=2)]

        result = await governance_node(state)

        # Must have reviews regardless of AI state
        assert "approved_content" in result or "rejected_content" in result

    async def test_high_quality_content_still_approved_when_ai_fails(self):
        """Content meeting all thresholds is approved even if AI is down."""
        state = make_initial_state("news", {})
        state["content_drafts"] = [_draft_with_scores(
            confidence=90.0,
            source_count=3,
            brand_alignment=85.0,
            risk_score=10.0,
        )]

        # AI fails completely
        mock_gateway = AsyncMock()
        mock_gateway.complete = AsyncMock(side_effect=Exception("AI totally down"))

        with patch("sfc.graph.nodes.governance.get_ai_gateway", return_value=mock_gateway, create=True):
            result = await governance_node(state)

        # High-quality content should be approved by code check
        assert len(result.get("approved_content", [])) > 0, \
            "High-quality content must be approved by code check even when AI fails"

    async def test_ai_cannot_modify_confidence_or_source_count(self):
        """persona_layer and editorial nodes must not modify confidence or source_count."""
        from sfc.graph.nodes.persona_layer import persona_layer_node

        state = make_initial_state("match_report", {})
        draft = _draft_with_scores(confidence=70.0, source_count=1)
        state["content_drafts"] = [draft]

        persona_result = await persona_layer_node(state)

        # Check that if content_drafts were returned, scores were NOT modified
        returned_drafts = persona_result.get("content_drafts", [])
        for d in returned_drafts:
            assert d["scores"]["confidence_score"] == 70.0, \
                "persona_layer must not modify confidence_score"
            assert d["scores"]["source_count"] == 1, \
                "persona_layer must not modify source_count"
