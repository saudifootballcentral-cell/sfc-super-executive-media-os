"""Central AI gateway — process-level singleton.

All AI calls in SFC go through this gateway.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any

from sfc.ai.cost_tracker import CallRecord, get_cost_tracker
from sfc.ai.fallback_manager import FallbackManager
from sfc.ai.model_policy import ModelPolicy
from sfc.ai.models import ModelRequest, ModelResponse
from sfc.ai.structured_output import extract_json, get_schema_class, validate_output

logger = logging.getLogger("sfc.ai.gateway")


class AIGateway:
    """All AI calls in SFC go through this gateway."""

    def __init__(self) -> None:
        self._policy = ModelPolicy()
        self._fallback_manager = FallbackManager()
        self._metrics: dict[str, Any] = {
            "total_calls": 0,
            "successful_calls": 0,
            "fallback_calls": 0,
            "failed_calls": 0,
            "validation_failures": 0,
        }

    async def complete(self, request: ModelRequest) -> ModelResponse:
        """Route request to appropriate provider via policy, return validated response.

        Never raises exceptions — always returns a ModelResponse.
        """
        self._metrics["total_calls"] += 1

        cost_tracker = get_cost_tracker()

        # Budget check
        if not cost_tracker.check_budget():
            logger.warning("[AIGateway] Budget exceeded — using deterministic fallback")
            self._metrics["fallback_calls"] += 1
            response = self._fallback_manager.get_fallback(request)
            self._record_call(request, response)
            return response

        # Select policy rule
        rule = self._policy.select(request)

        # Inject model into request context for provider
        primary_request = request.model_copy(
            update={"context": {**request.context, "model": rule.model}}
        )

        # Try primary provider
        primary_provider = self._get_provider(rule.provider)
        response = None

        if primary_provider is not None and primary_provider.is_available():
            try:
                response = await primary_provider.complete(primary_request)
            except Exception as exc:
                logger.warning(
                    "[AIGateway] Primary provider %s raised exception: %s",
                    rule.provider, exc,
                )
                response = None

        # Try fallback provider if primary failed
        if response is None or not response.success:
            if response is not None:
                logger.warning(
                    "[AIGateway] Primary %s/%s failed: %s — trying fallback %s/%s",
                    rule.provider, rule.model,
                    response.error,
                    rule.fallback_provider, rule.fallback_model,
                )

            fallback_request = request.model_copy(
                update={"context": {**request.context, "model": rule.fallback_model}}
            )
            fallback_provider = self._get_provider(rule.fallback_provider)

            if fallback_provider is not None and fallback_provider.is_available():
                try:
                    response = await fallback_provider.complete(fallback_request)
                    if response.success:
                        logger.info(
                            "[AIGateway] Fallback %s/%s succeeded",
                            rule.fallback_provider, rule.fallback_model,
                        )
                except Exception as exc:
                    logger.warning(
                        "[AIGateway] Fallback provider %s raised exception: %s",
                        rule.fallback_provider, exc,
                    )
                    response = None

        # If both providers failed, use deterministic fallback
        if response is None or not response.success:
            logger.warning(
                "[AIGateway] All AI providers failed for task_type=%s — using deterministic fallback",
                request.task_type,
            )
            self._metrics["fallback_calls"] += 1
            response = self._fallback_manager.get_fallback(request)
        else:
            self._metrics["successful_calls"] += 1

        # Structured output validation
        if request.output_schema and response.success and not response.used_fallback:
            schema_cls = get_schema_class(request.output_schema)
            if schema_cls is not None:
                instance, error = validate_output(response.text, schema_cls)
                if instance is not None:
                    response = response.model_copy(update={"parsed": instance.model_dump()})
                else:
                    logger.warning(
                        "[AIGateway] Output validation failed for %s: %s",
                        request.output_schema, error,
                    )
                    response = response.model_copy(update={"validation_failed": True})
                    self._metrics["validation_failures"] += 1
            else:
                # Try generic JSON extraction
                extracted = extract_json(response.text)
                if extracted:
                    response = response.model_copy(update={"parsed": extracted})

        # Record cost
        self._record_call(request, response)

        return response

    def _record_call(self, request: ModelRequest, response: ModelResponse) -> None:
        """Record the call in the cost tracker."""
        try:
            cost_tracker = get_cost_tracker()
            record = CallRecord(
                timestamp=datetime.utcnow().isoformat(),
                task_type=request.task_type,
                provider=response.provider,
                model=response.model,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                cost_usd=response.cost_usd,
                latency_ms=response.latency_ms,
                success=response.success,
                used_fallback=response.used_fallback,
                validation_failed=response.validation_failed,
            )
            cost_tracker.record(record)
        except Exception as exc:
            logger.warning("[AIGateway] Failed to record call: %s", exc)

    def _get_provider(self, provider_name: str):
        """Return provider instance by name."""
        try:
            if provider_name == "claude":
                from sfc.ai.providers.claude import ClaudeProvider
                return ClaudeProvider()
            if provider_name == "openai":
                from sfc.ai.providers.openai_provider import OpenAIProvider
                return OpenAIProvider()
            if provider_name == "gemini":
                from sfc.ai.providers.gemini_provider import GeminiProvider
                return GeminiProvider()
        except Exception as exc:
            logger.warning("[AIGateway] Could not load provider %s: %s", provider_name, exc)
        return None

    def get_metrics(self) -> dict:
        """Return observability metrics."""
        cost_tracker = get_cost_tracker()
        return {
            **self._metrics,
            "cost_report": cost_tracker.get_report(),
        }

    def health_check(self) -> dict:
        """Return provider health."""
        providers = {}
        for name in ("claude", "openai", "gemini"):
            provider = self._get_provider(name)
            if provider is not None:
                providers[name] = provider.health_check()
            else:
                providers[name] = {"available": False, "error": "Could not load provider"}

        return {
            "gateway": "healthy",
            "providers": providers,
            "metrics": self._metrics,
        }


# Process-level singleton
_instance: AIGateway | None = None


def get_ai_gateway() -> AIGateway:
    """Return process-level singleton AIGateway."""
    global _instance
    if _instance is None:
        _instance = AIGateway()
    return _instance
