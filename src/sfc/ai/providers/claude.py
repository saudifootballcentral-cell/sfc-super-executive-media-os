"""Claude (Anthropic) AI provider."""

from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from typing import Any

from sfc.ai.models import ModelRequest, ModelResponse
from sfc.ai.providers.base import AIProvider

logger = logging.getLogger("sfc.ai.providers.claude")

_DEFAULT_TIMEOUT = 30
_DEFAULT_MAX_RETRIES = 3

# All Claude 4.x models (e.g. claude-opus-4-8, claude-sonnet-4-6, claude-haiku-4-5-*)
# and the Claude 5 family (Fable 5, Mythos 5) reject temperature/top_p/top_k (HTTP 400).
_CLAUDE_4X_RE = re.compile(r"^claude-[a-z]+-4-")
_NO_SAMPLING_PARAMS_PREFIXES = (
    "claude-fable-5",
    "claude-mythos-5",
)


def _supports_temperature(model: str) -> bool:
    if _CLAUDE_4X_RE.match(model):
        return False
    return not any(model.startswith(prefix) for prefix in _NO_SAMPLING_PARAMS_PREFIXES)


class ClaudeProvider(AIProvider):
    """Async Claude provider using the anthropic library."""

    def is_available(self) -> bool:
        return os.environ.get("ANTHROPIC_API_KEY", "") != ""

    def health_check(self) -> dict:
        return {
            "provider": "claude",
            "available": self.is_available(),
            "api_key_set": self.is_available(),
        }

    async def complete(self, request: ModelRequest) -> ModelResponse:
        """Complete a request using the Anthropic API."""
        try:
            import anthropic
        except ImportError:
            return ModelResponse(
                success=False,
                error="anthropic package not installed",
                provider="claude",
                model=request.context.get("model", "unknown"),
            )

        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            return ModelResponse(
                success=False,
                error="ANTHROPIC_API_KEY not set",
                provider="claude",
                model=request.context.get("model", "unknown"),
            )

        model = request.context.get("model", "claude-sonnet-4-6")
        timeout = int(os.environ.get("AI_TIMEOUT_SECONDS", _DEFAULT_TIMEOUT))
        max_retries = int(os.environ.get("AI_MAX_RETRIES", _DEFAULT_MAX_RETRIES))

        client = anthropic.AsyncAnthropic(api_key=api_key)

        user_message = request.user_message
        if request.json_mode:
            user_message += "\n\nRespond with valid JSON only. No markdown, no explanation."

        for attempt in range(max_retries):
            try:
                start_ms = time.monotonic()
                create_kwargs: dict[str, Any] = {
                    "model": model,
                    "max_tokens": request.max_tokens,
                    "system": request.system_prompt,
                    "messages": [{"role": "user", "content": user_message}],
                }
                if _supports_temperature(model):
                    create_kwargs["temperature"] = request.temperature
                message = await asyncio.wait_for(
                    client.messages.create(**create_kwargs),
                    timeout=timeout,
                )
                latency_ms = int((time.monotonic() - start_ms) * 1000)

                raw_text = message.content[0].text.strip()
                input_tokens = message.usage.input_tokens
                output_tokens = message.usage.output_tokens

                from sfc.ai.cost_tracker import estimate_cost
                cost = estimate_cost(model, input_tokens, output_tokens)

                logger.info(
                    "[Claude] %s | %d+%d tokens | $%.6f | %dms",
                    model, input_tokens, output_tokens, cost, latency_ms,
                )

                return ModelResponse(
                    success=True,
                    text=raw_text,
                    provider="claude",
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost_usd=cost,
                    latency_ms=latency_ms,
                )

            except asyncio.TimeoutError:
                logger.warning(
                    "[Claude] Attempt %d/%d timed out after %ds",
                    attempt + 1, max_retries, timeout,
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    return ModelResponse(
                        success=False,
                        error=f"Timeout after {timeout}s (all {max_retries} attempts)",
                        provider="claude",
                        model=model,
                    )

            except Exception as exc:
                wait = 2 ** attempt
                logger.warning(
                    "[Claude] Attempt %d/%d failed: %s — retrying in %ds",
                    attempt + 1, max_retries, exc, wait,
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(wait)
                else:
                    return ModelResponse(
                        success=False,
                        error=f"All {max_retries} attempts failed: {exc}",
                        provider="claude",
                        model=model,
                    )

        return ModelResponse(
            success=False,
            error="Exhausted retries",
            provider="claude",
            model=model,
        )
