"""Tests for system behaviour when no API keys are set."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from sfc.ai.model_gateway import AIGateway
from sfc.ai.models import ModelRequest, ModelResponse
from sfc.ai.providers.claude import ClaudeProvider
from sfc.ai.providers.openai_provider import OpenAIProvider
from sfc.ai.providers.gemini_provider import GeminiProvider
from sfc.graph.state import make_initial_state


def _no_keys_env() -> dict:
    """Return env dict with all AI keys removed."""
    env = dict(os.environ)
    env.pop("ANTHROPIC_API_KEY", None)
    env.pop("OPENAI_API_KEY", None)
    env.pop("GEMINI_API_KEY", None)
    return env


def _make_request(task_type: str = "editorial") -> ModelRequest:
    return ModelRequest(
        task_type=task_type,
        system_prompt="Test",
        user_message="Test",
    )


class TestMissingAPIKeys:
    async def test_gateway_falls_back_when_no_anthropic_key(self):
        """Gateway returns deterministic fallback when ANTHROPIC_API_KEY is missing."""
        env = _no_keys_env()
        with patch.dict("os.environ", env, clear=True):
            gateway = AIGateway()
            response = await gateway.complete(_make_request("editorial"))

        assert isinstance(response, ModelResponse)
        assert response.used_fallback is True

    async def test_gateway_falls_back_when_no_openai_key(self):
        """Gateway falls back when OPENAI_API_KEY is missing and openai is the provider."""
        env = _no_keys_env()
        with patch.dict("os.environ", env, clear=True):
            gateway = AIGateway()
            response = await gateway.complete(_make_request("summary"))

        assert isinstance(response, ModelResponse)
        # Should still work via fallback
        assert response is not None

    async def test_provider_is_available_returns_false_without_key(self):
        """All providers return is_available=False when their key is missing."""
        env = _no_keys_env()
        with patch.dict("os.environ", env, clear=True):
            claude = ClaudeProvider()
            openai = OpenAIProvider()
            gemini = GeminiProvider()

            assert claude.is_available() is False
            assert openai.is_available() is False
            assert gemini.is_available() is False

    async def test_full_pipeline_runs_without_any_api_keys(self):
        """The full graph pipeline completes without any API keys configured."""
        from sfc.graph.nodes.intelligence import intelligence_node
        from sfc.graph.nodes.editorial import editorial_node
        from sfc.graph.nodes.learning import learning_node

        env = _no_keys_env()
        state = make_initial_state("news", {
            "headline": "Test headline",
            "sources": [
                {"name": "BBC", "reliability": 90},
                {"name": "Goal.com", "reliability": 85},
            ],
        })

        with patch.dict("os.environ", env, clear=True):
            intel_result = await intelligence_node(state)
            assert "intelligence_report" in intel_result

            state.update(intel_result)
            state["execution_plan"] = {"content_types": ["article"], "platforms_targeted": ["x"]}
            editorial_result = await editorial_node(state)
            assert "content_drafts" in editorial_result

            state.update(editorial_result)
            learning_result = await learning_node(state)
            assert "lessons_learned" in learning_result
            assert isinstance(learning_result["lessons_learned"], list)

    async def test_claude_provider_returns_error_without_key(self):
        """ClaudeProvider.complete returns ModelResponse with success=False when key missing."""
        env = _no_keys_env()
        with patch.dict("os.environ", env, clear=True):
            provider = ClaudeProvider()
            response = await provider.complete(_make_request())

        assert response.success is False
        assert response.error != ""

    async def test_gateway_never_raises_even_without_keys(self):
        """Gateway never raises exceptions even with no API keys."""
        env = _no_keys_env()
        with patch.dict("os.environ", env, clear=True):
            gateway = AIGateway()
            # Should never raise
            response = await gateway.complete(_make_request("executive"))

        assert isinstance(response, ModelResponse)
