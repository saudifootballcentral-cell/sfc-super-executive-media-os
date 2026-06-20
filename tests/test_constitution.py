"""Tests enforcing constitutional rules via the LangGraph governance node."""

import asyncio
import pytest

from sfc.core.constitution import get_governance_rules, load_constitution
from sfc.graph.nodes.governance import governance_node, _review_draft
from sfc.graph.state import SFCState, make_initial_state


# ---------------------------------------------------------------------------
# Constitution loader
# ---------------------------------------------------------------------------

class TestConstitutionLoader:
    def test_load_constitution_returns_string(self):
        text = load_constitution()
        assert isinstance(text, str)
        assert len(text) > 100

    def test_constitution_contains_executive_identity(self):
        text = load_constitution()
        assert "SFC Super Executive" in text

    def test_governance_rules_thresholds(self):
        rules = get_governance_rules()
        assert rules["min_confidence_score"] == 85.0
        assert rules["min_source_count"] == 2
        assert rules["min_brand_alignment_score"] == 70.0


# ---------------------------------------------------------------------------
# Governance — Verification Policy (min 2 sources)
# ---------------------------------------------------------------------------

class TestVerificationPolicy:
    def _draft(self, source_count: int, confidence: float = 90.0) -> dict:
        return {
            "content_id": "test-001",
            "title": "Test Article",
            "body": "Test body",
            "scores": {
                "confidence_score": confidence,
                "risk_score": 100.0 - confidence,
                "source_count": source_count,
                "brand_alignment_score": 85.0,
            },
            "is_rumor": False,
            "rumor_label": None,
            "platforms": ["x"],
            "division": "editorial",
        }

    def _rules(self):
        return get_governance_rules()

    def test_two_sources_passes(self):
        rules = self._rules()
        review = _review_draft(self._draft(2), rules["min_confidence_score"],
                               rules["min_source_count"], rules["min_brand_alignment_score"],
                               rules["max_risk_score_before_escalation"])
        assert review["approved"]

    def test_one_source_fails(self):
        rules = self._rules()
        review = _review_draft(self._draft(1), rules["min_confidence_score"],
                               rules["min_source_count"], rules["min_brand_alignment_score"],
                               rules["max_risk_score_before_escalation"])
        assert not review["approved"]
        assert any("source" in r.lower() for r in review["reasons"])

    def test_zero_sources_fails(self):
        rules = self._rules()
        review = _review_draft(self._draft(0), rules["min_confidence_score"],
                               rules["min_source_count"], rules["min_brand_alignment_score"],
                               rules["max_risk_score_before_escalation"])
        assert not review["approved"]


# ---------------------------------------------------------------------------
# Governance — Confidence Policy (>= 85 required)
# ---------------------------------------------------------------------------

class TestConfidencePolicy:
    def _draft(self, confidence: float, source_count: int = 2) -> dict:
        return {
            "content_id": "test-002",
            "title": "Confidence Test",
            "body": "Body",
            "scores": {
                "confidence_score": confidence,
                "risk_score": 100.0 - confidence,
                "source_count": source_count,
                "brand_alignment_score": 85.0,
            },
            "is_rumor": False,
            "rumor_label": None,
        }

    def _r(self):
        return get_governance_rules()

    def test_confidence_84_rejected_and_escalated(self):
        r = self._r()
        review = _review_draft(self._draft(84.9), r["min_confidence_score"],
                               r["min_source_count"], r["min_brand_alignment_score"],
                               r["max_risk_score_before_escalation"])
        assert not review["approved"]
        assert review["escalated"]

    def test_confidence_exactly_85_passes(self):
        r = self._r()
        review = _review_draft(self._draft(85.0), r["min_confidence_score"],
                               r["min_source_count"], r["min_brand_alignment_score"],
                               r["max_risk_score_before_escalation"])
        assert review["approved"]

    def test_confidence_100_passes(self):
        r = self._r()
        review = _review_draft(self._draft(100.0), r["min_confidence_score"],
                               r["min_source_count"], r["min_brand_alignment_score"],
                               r["max_risk_score_before_escalation"])
        assert review["approved"]


# ---------------------------------------------------------------------------
# Governance — Rumor Policy
# ---------------------------------------------------------------------------

class TestRumorPolicy:
    def _draft(self, is_rumor: bool, label: str | None) -> dict:
        return {
            "content_id": "rumor-001",
            "title": "Rumor Test",
            "body": "Body",
            "scores": {
                "confidence_score": 90.0,
                "risk_score": 10.0,
                "source_count": 2,
                "brand_alignment_score": 85.0,
            },
            "is_rumor": is_rumor,
            "rumor_label": label,
        }

    def _r(self):
        return get_governance_rules()

    def test_unlabeled_rumor_rejected(self):
        r = self._r()
        review = _review_draft(self._draft(True, None), r["min_confidence_score"],
                               r["min_source_count"], r["min_brand_alignment_score"],
                               r["max_risk_score_before_escalation"])
        assert not review["approved"]
        assert any("rumor" in reason.lower() for reason in review["reasons"])

    def test_labeled_rumor_passes_other_checks(self):
        r = self._r()
        review = _review_draft(self._draft(True, "RUMOR — unconfirmed"),
                               r["min_confidence_score"], r["min_source_count"],
                               r["min_brand_alignment_score"], r["max_risk_score_before_escalation"])
        assert review["approved"]

    def test_non_rumor_always_allowed(self):
        r = self._r()
        review = _review_draft(self._draft(False, None), r["min_confidence_score"],
                               r["min_source_count"], r["min_brand_alignment_score"],
                               r["max_risk_score_before_escalation"])
        assert review["approved"]


# ---------------------------------------------------------------------------
# Full governance node (async)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestGovernanceNode:
    def _state_with_drafts(self, drafts: list[dict]) -> dict:
        state = make_initial_state("news", {"headline": "test"})
        state["content_drafts"] = drafts
        return state

    async def test_all_approved_when_scores_good(self):
        drafts = [
            {
                "content_id": f"c{i}",
                "title": f"Article {i}",
                "body": "body",
                "platforms": ["x"],
                "scores": {
                    "confidence_score": 90.0,
                    "risk_score": 10.0,
                    "source_count": 3,
                    "brand_alignment_score": 85.0,
                },
                "is_rumor": False,
                "rumor_label": None,
            }
            for i in range(3)
        ]
        result = await governance_node(self._state_with_drafts(drafts))
        assert len(result["approved_content"]) == 3
        assert len(result["rejected_content"]) == 0

    async def test_all_rejected_when_confidence_low(self):
        drafts = [
            {
                "content_id": "low-conf",
                "title": "Low confidence",
                "body": "body",
                "scores": {
                    "confidence_score": 50.0,
                    "risk_score": 50.0,
                    "source_count": 2,
                    "brand_alignment_score": 85.0,
                },
                "is_rumor": False,
                "rumor_label": None,
            }
        ]
        result = await governance_node(self._state_with_drafts(drafts))
        assert len(result["rejected_content"]) == 1
        assert len(result["approved_content"]) == 0

    async def test_empty_drafts_returns_empty(self):
        result = await governance_node(self._state_with_drafts([]))
        assert result["approved_content"] == []
        assert result["rejected_content"] == []
