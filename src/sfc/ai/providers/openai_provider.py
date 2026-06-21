"""OpenAI AI provider — lazy import so openai is optional."""

from __future__ import annotations

import asyncio
import logging
import os
import time

from sfc.ai.models import ModelRequest, ModelResponse
from sfc.ai.providers.base import AIProvider

logger = logging.getLogger("sfc.ai.providers.openai")

_DEFAULT_TIMEOUT = 30
_DEFAULT_MAX_RETRIES = 3


class OpenAIProvider(AIProvider):
    """OpenAI provider using the openai library (lazy import)."""

    def is_available(self) -> bool:
        if os.environ.get("OPENAI_API_KEY", "") == "":
            return False
        try:
            import openai  # noqa: F401
            return True
        except ImportError:
            return False

    def health_check(self) -> dict:
        key_set = os.environ.get("OPENAI_API_KEY", "") != ""
        try:
            import openai  # noqa: F401
            lib_installed = True
        except ImportError:
            lib_installed = False

        return {
            "provider": "openai",
            "available": key_set and lib_installed,
            "api_key_set": key_set,
            "library_installed": lib_installed,
        }

    async def complete(self, request: ModelRequest) -> ModelResponse:
        """Complete a request using the OpenAI API."""
        try:
            import openai
        except ImportError:
            return ModelResponse(
                success=False,
                error="openai package not installed",
                provider="openai",
                model=request.context.get("model", "unknown"),
            )

        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            return ModelResponse(
                success=False,
                error="OPENAI_API_KEY not set",
                provider="openai",
                model=request.context.get("model", "unknown"),
            )

        model = request.context.get("model", "gpt-4o-mini")
        timeout = int(os.environ.get("AI_TIMEOUT_SECONDS", _DEFAULT_TIMEOUT))
        max_retries = int(os.environ.get("AI_MAX_RETRIES", _DEFAULT_MAX_RETRIES))

        client = openai.AsyncOpenAI(api_key=api_key)

        messages = [
            {"role": "system", "content": request.system_prompt},
            {"role": "user", "content": request.user_message},
        ]
        if request.json_mode:
            messages[-1]["content"] += "\n\nRespond with valid JSON only."

        for attempt in range(max_retries):
            try:
                start_ms = time.monotonic()
                response = await asyncio.wait_for(
                    client.chat.completions.create(
                        model=model,
                        max_tokens=request.max_tokens,
                        temperature=request.temperature,
                        messages=messages,
                    ),
                    timeout=timeout,
                )
                latency_ms = int((time.monotonic() - start_ms) * 1000)

                raw_text = response.choices[0].message.content or ""
                input_tokens = response.usage.prompt_tokens if response.usage else 0
                output_tokens = response.usage.completion_tokens if response.usage else 0

                from sfc.ai.cost_tracker import estimate_cost
                cost = estimate_cost(model, input_tokens, output_tokens)

                logger.info(
                    "[OpenAI] %s | %d+%d tokens | $%.6f | %dms",
                    model, input_tokens, output_tokens, cost, latency_ms,
                )

                return ModelResponse(
                    success=True,
                    text=raw_text.strip(),
                    provider="openai",
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost_usd=cost,
                    latency_ms=latency_ms,
                )

            except asyncio.TimeoutError:
                logger.warning(
                    "[OpenAI] Attempt %d/%d timed out after %ds",
                    attempt + 1, max_retries, timeout,
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    return ModelResponse(
                        success=False,
                        error=f"Timeout after {timeout}s (all {max_retries} attempts)",
                        provider="openai",
                        model=model,
                    )

            except Exception as exc:
                wait = 2 ** attempt
                logger.warning(
                    "[OpenAI] Attempt %d/%d failed: %s — retrying in %ds",
                    attempt + 1, max_retries, exc, wait,
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(wait)
                else:
                    return ModelResponse(
                        success=False,
                        error=f"All {max_retries} attempts failed: {exc}",
                        provider="openai",
                        model=model,
                    )

        return ModelResponse(
            success=False,
            error="Exhausted retries",
            provider="openai",
            model=model,
        )
