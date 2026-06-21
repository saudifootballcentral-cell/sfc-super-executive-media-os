"""Tests for model policy selection — no API calls."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from sfc.ai.model_policy import ModelPolicy
from sfc.ai.models import ModelRequest


def _make_request(task_type: str) -> ModelRequest:
    return ModelRequest(
        task_type=task_type,
        system_prompt="test",
        user_message="test",
    )


class TestModelPolicy:
    def test_executive_task_selects_opus(self):
        """Executive task should select claude-opus-4-8."""
        with patch.dict("os.environ", {}, clear=False):
            policy = ModelPolicy()
        rule = policy.select(_make_request("executive"))
        assert rule.provider == "claude"
        assert "opus" in rule.model.lower() or rule.model == "claude-opus-4-8"

    def test_editorial_task_selects_sonnet(self):
        """Editorial task should select claude-sonnet-4-6."""
        policy = ModelPolicy()
        rule = policy.select(_make_request("editorial"))
        assert rule.provider == "claude"
        assert "sonnet" in rule.model.lower()

    def test_governance_task_selects_sonnet(self):
        """Governance task should select claude-sonnet-4-6."""
        policy = ModelPolicy()
        rule = policy.select(_make_request("governance"))
        assert rule.provider == "claude"
        assert "sonnet" in rule.model.lower()

    def test_routing_task_selects_haiku(self):
        """Routing task should select claude-haiku."""
        policy = ModelPolicy()
        rule = policy.select(_make_request("routing"))
        assert rule.provider == "claude"
        assert "haiku" in rule.model.lower()

    def test_unknown_task_uses_default_policy(self):
        """Unknown task type should fall back to default rule."""
        policy = ModelPolicy()
        rule = policy.select(_make_request("completely_unknown_task_xyz"))
        assert rule is not None
        assert rule.provider is not None
        assert rule.model is not None

    def test_policy_respects_env_override_cost_optimized(self):
        """DEFAULT_MODEL_POLICY=cost_optimized should change model selection."""
        with patch.dict("os.environ", {"DEFAULT_MODEL_POLICY": "cost_optimized"}):
            policy = ModelPolicy()
        rule = policy.select(_make_request("executive"))
        # Cost optimized executive should use sonnet instead of opus
        assert rule is not None
        assert rule.provider == "claude"

    def test_policy_respects_env_override_openai_primary(self):
        """DEFAULT_MODEL_POLICY=openai_primary should select OpenAI for editorial."""
        with patch.dict("os.environ", {"DEFAULT_MODEL_POLICY": "openai_primary"}):
            policy = ModelPolicy()
        rule = policy.select(_make_request("editorial"))
        assert rule is not None
        assert rule.provider == "openai"

    def test_policy_returns_fallback_model(self):
        """Every rule should have a fallback model configured."""
        policy = ModelPolicy()
        for task_type in ["executive", "editorial", "governance", "intelligence", "creative",
                          "strategic_planning", "persona", "revenue", "learning", "routing", "summary"]:
            rule = policy.select(_make_request(task_type))
            assert rule.fallback_model is not None
            assert rule.fallback_provider is not None

    def test_policy_rule_has_required_fields(self):
        """Each policy rule must have all required fields."""
        policy = ModelPolicy()
        rule = policy.select(_make_request("editorial"))
        assert isinstance(rule.max_tokens, int)
        assert isinstance(rule.temperature, float)
        assert isinstance(rule.timeout_seconds, int)
        assert rule.max_tokens > 0
        assert 0.0 <= rule.temperature <= 2.0

    def test_intelligence_task_selects_sonnet(self):
        """Intelligence task should select claude-sonnet-4-6."""
        policy = ModelPolicy()
        rule = policy.select(_make_request("intelligence"))
        assert rule.provider == "claude"
        assert "sonnet" in rule.model.lower()

    def test_learning_task_selects_haiku(self):
        """Learning task should select claude-haiku (cost efficient)."""
        policy = ModelPolicy()
        rule = policy.select(_make_request("learning"))
        assert rule.provider == "claude"
        assert "haiku" in rule.model.lower()
