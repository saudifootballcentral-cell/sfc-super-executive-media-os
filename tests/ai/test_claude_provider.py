"""Regression tests for ClaudeProvider — temperature exclusion and permanent-error handling.

These tests verify that claude-opus-4-8 (and all other Claude 4.x models) never include
temperature/top_p/top_k in the Anthropic API payload, and that permanent errors (400s,
deprecated-param errors) are not retried.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sfc.ai.models import ModelRequest, ModelResponse
from sfc.ai.providers.claude import (
    ClaudeProvider,
    _is_permanent_error,
    _supports_temperature,
)


# ---------------------------------------------------------------------------
# _supports_temperature unit tests
# ---------------------------------------------------------------------------

class TestSupportsTemperature:
    def test_opus_4_8_returns_false(self) -> None:
        assert _supports_temperature("claude-opus-4-8") is False

    def test_sonnet_4_6_returns_false(self) -> None:
        assert _supports_temperature("claude-sonnet-4-6") is False

    def test_haiku_4_5_returns_false(self) -> None:
        assert _supports_temperature("claude-haiku-4-5-20251001") is False

    def test_fable_5_returns_false(self) -> None:
        assert _supports_temperature("claude-fable-5") is False

    def test_mythos_5_returns_false(self) -> None:
        assert _supports_temperature("claude-mythos-5") is False

    def test_claude_3_opus_returns_true(self) -> None:
        # Legacy 3.x models still accept temperature
        assert _supports_temperature("claude-3-opus-20240229") is True

    def test_claude_3_sonnet_returns_true(self) -> None:
        assert _supports_temperature("claude-3-sonnet-20240229") is True


# ---------------------------------------------------------------------------
# _is_permanent_error unit tests
# ---------------------------------------------------------------------------

class TestIsPermanentError:
    def _exc(self, msg: str, status: int | None = None) -> Exception:
        exc = Exception(msg)
        if status is not None:
            exc.status_code = status  # type: ignore[attr-defined]
        return exc

    def test_400_is_permanent(self) -> None:
        assert _is_permanent_error(self._exc("bad request", status=400)) is True

    def test_401_is_permanent(self) -> None:
        assert _is_permanent_error(self._exc("unauthorized", status=401)) is True

    def test_403_is_permanent(self) -> None:
        assert _is_permanent_error(self._exc("forbidden", status=403)) is True

    def test_temperature_deprecated_message_is_permanent(self) -> None:
        assert _is_permanent_error(self._exc("temperature is deprecated for this model")) is True

    def test_invalid_request_error_is_permanent(self) -> None:
        assert _is_permanent_error(self._exc("invalid_request_error: bad field")) is True

    def test_500_is_not_permanent(self) -> None:
        assert _is_permanent_error(self._exc("server error", status=500)) is False

    def test_timeout_is_not_permanent(self) -> None:
        assert _is_permanent_error(self._exc("request timed out")) is False

    def test_network_error_is_not_permanent(self) -> None:
        assert _is_permanent_error(self._exc("connection reset by peer")) is False


# ---------------------------------------------------------------------------
# ClaudeProvider payload-capture tests
# ---------------------------------------------------------------------------

def _make_request(model: str, temperature: float = 0.3) -> ModelRequest:
    return ModelRequest(
        task_type="executive",
        system_prompt="You are a test assistant.",
        user_message="Test message.",
        max_tokens=64,
        temperature=temperature,
        context={"model": model},
    )


def _fake_message(text: str = '{"routing": "planning"}') -> MagicMock:
    msg = MagicMock()
    msg.content = [MagicMock(text=text)]
    msg.usage.input_tokens = 100
    msg.usage.output_tokens = 20
    return msg


class TestClaudeProviderPayload:
    """Verify the exact kwargs sent to client.messages.create."""

    async def _run_with_capture(self, model: str) -> dict:
        """Run ClaudeProvider.complete() for the given model and return captured kwargs."""
        captured: dict = {}

        async def fake_create(**kwargs):
            captured.update(kwargs)
            return _fake_message()

        mock_messages = MagicMock()
        mock_messages.create = fake_create
        mock_client = MagicMock()
        mock_client.messages = mock_messages

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-test-key"}):
            with patch("anthropic.AsyncAnthropic", return_value=mock_client):
                provider = ClaudeProvider()
                req = _make_request(model, temperature=0.3)
                await provider.complete(req)

        return captured

    @pytest.mark.asyncio
    async def test_opus_4_8_payload_has_no_temperature(self) -> None:
        """claude-opus-4-8 must never send temperature to the Anthropic API."""
        captured = await self._run_with_capture("claude-opus-4-8")
        assert "temperature" not in captured, (
            f"claude-opus-4-8 must not include temperature; payload keys: {sorted(captured)}"
        )
        assert captured.get("model") == "claude-opus-4-8"

    @pytest.mark.asyncio
    async def test_sonnet_4_6_payload_has_no_temperature(self) -> None:
        """claude-sonnet-4-6 must never send temperature to the Anthropic API."""
        captured = await self._run_with_capture("claude-sonnet-4-6")
        assert "temperature" not in captured, (
            f"claude-sonnet-4-6 must not include temperature; payload keys: {sorted(captured)}"
        )

    @pytest.mark.asyncio
    async def test_haiku_4_5_payload_has_no_temperature(self) -> None:
        """claude-haiku-4-5-20251001 must never send temperature."""
        captured = await self._run_with_capture("claude-haiku-4-5-20251001")
        assert "temperature" not in captured

    @pytest.mark.asyncio
    async def test_payload_always_includes_required_keys(self) -> None:
        """model, max_tokens, system, messages must always be present."""
        captured = await self._run_with_capture("claude-opus-4-8")
        for key in ("model", "max_tokens", "system", "messages"):
            assert key in captured, f"Required key '{key}' missing from payload"


# ---------------------------------------------------------------------------
# Permanent-error no-retry test
# ---------------------------------------------------------------------------

class TestPermanentErrorHandling:
    @pytest.mark.asyncio
    async def test_temperature_error_not_retried(self) -> None:
        """A 'temperature is deprecated' error must return immediately without retrying."""
        call_count = 0

        async def fake_create(**kwargs):
            nonlocal call_count
            call_count += 1
            exc = Exception("temperature is deprecated for this model")
            exc.status_code = 400  # type: ignore[attr-defined]
            raise exc

        mock_messages = MagicMock()
        mock_messages.create = fake_create
        mock_client = MagicMock()
        mock_client.messages = mock_messages

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-test-key"}):
            with patch("anthropic.AsyncAnthropic", return_value=mock_client):
                provider = ClaudeProvider()
                req = _make_request("claude-opus-4-8")
                response = await provider.complete(req)

        assert response.success is False
        assert "deprecated" in response.error.lower() or "temperature" in response.error.lower()
        assert call_count == 1, (
            f"Permanent error must not be retried — expected 1 attempt, got {call_count}"
        )

    @pytest.mark.asyncio
    async def test_network_error_is_retried(self) -> None:
        """A transient network error must be retried up to max_retries."""
        call_count = 0

        async def fake_create(**kwargs):
            nonlocal call_count
            call_count += 1
            raise ConnectionError("connection reset")

        mock_messages = MagicMock()
        mock_messages.create = fake_create
        mock_client = MagicMock()
        mock_client.messages = mock_messages

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-test-key"}):
            with patch("anthropic.AsyncAnthropic", return_value=mock_client):
                # Speed up: patch sleep to be instant
                with patch("asyncio.sleep", new=AsyncMock()):
                    provider = ClaudeProvider()
                    req = _make_request("claude-opus-4-8")
                    response = await provider.complete(req)

        assert response.success is False
        assert call_count == 3, (
            f"Transient error should be retried 3 times total, got {call_count}"
        )
