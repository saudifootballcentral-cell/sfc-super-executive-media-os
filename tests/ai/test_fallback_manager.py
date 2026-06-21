"""Tests for the fallback manager — no API calls."""

from __future__ import annotations

import pytest

from sfc.ai.fallback_manager import FallbackManager
from sfc.ai.models import ModelRequest, ModelResponse


def _make_request(task_type: str, context: dict | None = None) -> ModelRequest:
    return ModelRequest(
        task_type=task_type,
        system_prompt="test system",
        user_message="test message",
        context=context or {},
    )


class TestFallbackManager:
    async def test_executive_fallback_returns_valid_decision(self):
        """Executive fallback returns a dict with required decision fields."""
        manager = FallbackManager()
        response = manager.get_fallback(_make_request("executive", {"task_type": "transfer"}))

        assert isinstance(response, ModelResponse)
        assert response.used_fallback is True
        assert response.success is True
        assert "routing" in response.parsed
        assert response.parsed["routing"] == "planning"
        assert "recommended_divisions" in response.parsed
        assert isinstance(response.parsed["recommended_divisions"], list)

    async def test_editorial_fallback_returns_content_drafts(self):
        """Editorial fallback returns title, body, and content_type fields."""
        manager = FallbackManager()
        response = manager.get_fallback(_make_request("editorial", {"headline": "Test Headline"}))

        assert response.success is True
        assert response.used_fallback is True
        assert "title" in response.parsed
        assert "body" in response.parsed
        assert "content_type" in response.parsed

    async def test_intelligence_fallback_returns_report(self):
        """Intelligence fallback returns a valid intelligence report structure."""
        manager = FallbackManager()
        response = manager.get_fallback(_make_request("intelligence"))

        assert response.success is True
        assert response.used_fallback is True
        assert "summary" in response.parsed
        assert "key_facts" in response.parsed
        assert "confidence_score" in response.parsed
        assert isinstance(response.parsed["key_facts"], list)

    async def test_governance_fallback_returns_safe_result(self):
        """Governance fallback provides explanatory notes, not approval decisions."""
        manager = FallbackManager()
        response = manager.get_fallback(_make_request("governance"))

        assert response.success is True
        assert response.used_fallback is True
        # Should contain explanation/suggestions, NOT approval decisions
        assert "explanation" in response.parsed or "suggestions" in response.parsed

    async def test_unknown_task_fallback_returns_response(self):
        """Unknown task_type should still get a valid fallback response."""
        manager = FallbackManager()
        response = manager.get_fallback(_make_request("completely_unknown_xyz"))

        assert isinstance(response, ModelResponse)
        assert response.used_fallback is True
        assert response.success is True

    async def test_fallback_marked_as_fallback_in_response(self):
        """All fallback responses must have used_fallback=True."""
        manager = FallbackManager()
        for task_type in ["executive", "editorial", "intelligence", "governance",
                          "creative", "persona", "revenue", "learning", "routing"]:
            response = manager.get_fallback(_make_request(task_type))
            assert response.used_fallback is True, \
                f"Fallback response for {task_type} should have used_fallback=True"

    async def test_fallback_provider_is_fallback(self):
        """Fallback responses should identify as 'fallback' provider."""
        manager = FallbackManager()
        response = manager.get_fallback(_make_request("executive"))
        assert response.provider == "fallback"

    async def test_fallback_has_zero_cost(self):
        """Fallback responses should have zero cost (no API call)."""
        manager = FallbackManager()
        response = manager.get_fallback(_make_request("editorial"))
        assert response.cost_usd == 0.0

    async def test_creative_fallback_returns_brief(self):
        """Creative fallback returns a creative brief."""
        manager = FallbackManager()
        response = manager.get_fallback(_make_request("creative"))
        assert response.success is True
        assert "concept" in response.parsed or "visual_direction" in response.parsed

    async def test_learning_fallback_returns_lessons(self):
        """Learning fallback returns lessons list."""
        manager = FallbackManager()
        response = manager.get_fallback(_make_request("learning"))
        assert response.success is True
        assert "lessons" in response.parsed
        assert isinstance(response.parsed["lessons"], list)
