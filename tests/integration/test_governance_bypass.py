"""Tests that personas and war rooms cannot bypass the governance gate.

Constitutional requirement: All content must pass through governance_node
before reaching publishing_node, regardless of persona or war room output.
"""

from __future__ import annotations

import pytest

from sfc.graph.nodes.governance import governance_node
from sfc.graph.nodes.persona_layer import persona_layer_node
from sfc.graph.nodes.war_room_router import war_room_router_node
from sfc.graph.state import make_initial_state


def _draft_with_scores(
    confidence: float = 90.0,
    source_count: int = 3,
    brand_alignment: float = 85.0,
    risk_score: float = 10.0,
    is_rumor: bool = False,
):
    return {
        "content_id": "test-001",
        "title": "Test content",
        "body": "Test body content.",
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


class TestGovernanceBypassPrevention:
    async def test_governance_still_rejects_low_confidence_after_persona_enrichment(self):
        """Persona layer must not inflate confidence so that low-confidence content passes."""
        state = make_initial_state("match_report", {})
        state["content_drafts"] = [_draft_with_scores(confidence=70.0)]  # Below 85 threshold

        # Run persona layer
        persona_result = await persona_layer_node(state)
        state.update(persona_result)

        # Verify confidence score was NOT changed by persona layer
        for draft in state.get("content_drafts", []):
            assert draft["scores"]["confidence_score"] == 70.0, \
                "persona_layer must not modify confidence_score"

        # Governance should still reject it
        gov_result = await governance_node(state)
        assert len(gov_result.get("rejected_content", [])) > 0, \
            "Governance must reject low-confidence content even after persona enrichment"

    async def test_governance_still_rejects_insufficient_sources_after_persona(self):
        """Persona layer must not add phantom sources to bypass minimum source count."""
        state = make_initial_state("match_report", {})
        state["content_drafts"] = [_draft_with_scores(source_count=1)]  # Below min 2

        persona_result = await persona_layer_node(state)
        state.update(persona_result)

        # Verify source_count was NOT changed
        for draft in state.get("content_drafts", []):
            assert draft["scores"]["source_count"] == 1, \
                "persona_layer must not modify source_count"

        gov_result = await governance_node(state)
        assert len(gov_result.get("rejected_content", [])) > 0, \
            "Governance must reject insufficient-source content even after persona enrichment"

    async def test_war_room_state_does_not_appear_in_approved_content(self):
        """War room activation state must not automatically approve content."""
        state = make_initial_state("crisis", {})
        state["content_drafts"] = [_draft_with_scores(confidence=70.0, source_count=1)]

        war_result = await war_room_router_node(state)
        state.update(war_result)

        # War room router must not set approved_content
        assert state.get("approved_content", []) == [], \
            "War room router must not add items to approved_content"

    async def test_persona_layer_does_not_set_approved_content(self):
        """Persona layer must not add items to approved_content."""
        state = make_initial_state("match_report", {})
        state["content_drafts"] = [_draft_with_scores(confidence=90.0)]

        persona_result = await persona_layer_node(state)
        assert "approved_content" not in persona_result, \
            "persona_layer must not return approved_content"

    async def test_persona_layer_does_not_set_publish_queue(self):
        """Persona layer must not add items to publish_queue."""
        state = make_initial_state("match_report", {})
        state["content_drafts"] = [_draft_with_scores(confidence=90.0)]

        persona_result = await persona_layer_node(state)
        assert "publish_queue" not in persona_result, \
            "persona_layer must not return publish_queue"

    async def test_war_room_router_does_not_set_approved_content(self):
        war_result = await war_room_router_node(
            make_initial_state("crisis", {"crisis_type": "reputation_risk"})
        )
        assert "approved_content" not in war_result, \
            "war_room_router must not return approved_content"

    async def test_war_room_router_does_not_set_publish_queue(self):
        war_result = await war_room_router_node(
            make_initial_state("crisis", {})
        )
        assert "publish_queue" not in war_result, \
            "war_room_router must not return publish_queue"

    async def test_governance_still_enforces_confidence_threshold(self):
        """Run governance directly to confirm 85-point threshold holds."""
        state = make_initial_state("news", {})
        state["content_drafts"] = [_draft_with_scores(confidence=84.9)]
        state["verified_sources"] = [{"name": "BBC"}, {"name": "Goal.com"}]

        result = await governance_node(state)
        rejected = result.get("rejected_content", [])
        assert len(rejected) > 0, "Governance must reject confidence < 85"

    async def test_governance_still_enforces_min_source_count(self):
        """Run governance directly to confirm 2-source minimum holds."""
        state = make_initial_state("news", {})
        state["content_drafts"] = [_draft_with_scores(confidence=90.0, source_count=1)]
        state["verified_sources"] = [{"name": "BBC"}]

        result = await governance_node(state)
        rejected = result.get("rejected_content", [])
        assert len(rejected) > 0, "Governance must reject single-source content"
