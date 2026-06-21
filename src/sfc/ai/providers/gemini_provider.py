"""Gemini (Google) AI provider — lazy import so google-generativeai is optional."""

from __future__ import annotations

import asyncio
import logging
import os
import time

from sfc.ai.models import ModelRequest, ModelResponse
from sfc.ai.providers.base import AIProvider

logger = logging.getLogger("sfc.ai.providers.gemini")

_DEFAULT_TIMEOUT = 30
_DEFAULT_MAX_RETRIES = 3


class GeminiProvider(AIProvider):
    """Gemini provider using google.generativeai (lazy import)."""

    def is_available(self) -> bool:
        if os.environ.get("GEMINI_API_KEY", "") == "":
            return False
        try:
            import google.generativeai  # noqa: F401
            return True
        except ImportError:
            return False

    def health_check(self) -> dict:
        key_set = os.environ.get("GEMINI_API_KEY", "") != ""
        try:
            import google.generativeai  # noqa: F401
            lib_installed = True
        except ImportError:
            lib_installed = False

        return {
            "provider": "gemini",
            "available": key_set and lib_installed,
            "api_key_set": key_set,
            "library_installed": lib_installed,
        }

    async def complete(self, request: ModelRequest) -> ModelResponse:
        """Complete a request using the Gemini API."""
        try:
            import google.generativeai as genai
        except ImportError:
            return ModelResponse(
                success=False,
                error="google-generativeai package not installed",
                provider="gemini",
                model=request.context.get("model", "unknown"),
            )

        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            return ModelResponse(
                success=False,
                error="GEMINI_API_KEY not set",
                provider="gemini",
                model=request.context.get("model", "unknown"),
            )

        model_name = request.context.get("model", "gemini-1.5-flash")
        timeout = int(os.environ.get("AI_TIMEOUT_SECONDS", _DEFAULT_TIMEOUT))
        max_retries = int(os.environ.get("AI_MAX_RETRIES", _DEFAULT_MAX_RETRIES))

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=request.system_prompt,
        )

        user_content = request.user_message
        if request.json_mode:
            user_content += "\n\nRespond with valid JSON only."

        for attempt in range(max_retries):
            try:
                start_ms = time.monotonic()

                # Gemini's async API
                response = await asyncio.wait_for(
                    model.generate_content_async(user_content),
                    timeout=timeout,
                )
                latency_ms = int((time.monotonic() - start_ms) * 1000)

                raw_text = response.text.strip() if response.text else ""
                # Gemini doesn't always expose token counts easily
                input_tokens = 0
                output_tokens = 0
                if hasattr(response, "usage_metadata") and response.usage_metadata:
                    input_tokens = getattr(response.usage_metadata, "prompt_token_count", 0) or 0
                    output_tokens = getattr(response.usage_metadata, "candidates_token_count", 0) or 0

                from sfc.ai.cost_tracker import estimate_cost
                cost = estimate_cost(model_name, input_tokens, output_tokens)

                logger.info(
                    "[Gemini] %s | %d+%d tokens | $%.6f | %dms",
                    model_name, input_tokens, output_tokens, cost, latency_ms,
                )

                return ModelResponse(
                    success=True,
                    text=raw_text,
                    provider="gemini",
                    model=model_name,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost_usd=cost,
                    latency_ms=latency_ms,
                )

            except asyncio.TimeoutError:
                logger.warning(
                    "[Gemini] Attempt %d/%d timed out after %ds",
                    attempt + 1, max_retries, timeout,
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    return ModelResponse(
                        success=False,
                        error=f"Timeout after {timeout}s (all {max_retries} attempts)",
                        provider="gemini",
                        model=model_name,
                    )

            except Exception as exc:
                wait = 2 ** attempt
                logger.warning(
                    "[Gemini] Attempt %d/%d failed: %s — retrying in %ds",
                    attempt + 1, max_retries, exc, wait,
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(wait)
                else:
                    return ModelResponse(
                        success=False,
                        error=f"All {max_retries} attempts failed: {exc}",
                        provider="gemini",
                        model=model_name,
                    )

        return ModelResponse(
            success=False,
            error="Exhausted retries",
            provider="gemini",
            model=model_name,
        )
