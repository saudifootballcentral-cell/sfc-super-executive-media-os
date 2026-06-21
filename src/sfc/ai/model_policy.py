"""Policy-driven model selection. No node hardcodes a model name."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from sfc.ai.models import ModelRequest

logger = logging.getLogger("sfc.ai.model_policy")


@dataclass
class PolicyRule:
    task_type: str          # "executive", "editorial", "governance", etc.
    provider: str           # "claude", "openai", "gemini"
    model: str              # actual model id
    fallback_provider: str  # secondary provider
    fallback_model: str
    max_tokens: int
    temperature: float
    timeout_seconds: int


# Default policy table
_DEFAULT_RULES: list[PolicyRule] = [
    PolicyRule(
        task_type="executive",
        provider="claude", model="claude-opus-4-8",
        fallback_provider="claude", fallback_model="claude-sonnet-4-6",
        max_tokens=2048, temperature=0.3, timeout_seconds=60,
    ),
    PolicyRule(
        task_type="governance",
        provider="claude", model="claude-sonnet-4-6",
        fallback_provider="claude", fallback_model="claude-haiku-4-5-20251001",
        max_tokens=1024, temperature=0.1, timeout_seconds=30,
    ),
    PolicyRule(
        task_type="editorial",
        provider="claude", model="claude-sonnet-4-6",
        fallback_provider="openai", fallback_model="gpt-4o-mini",
        max_tokens=4096, temperature=0.7, timeout_seconds=30,
    ),
    PolicyRule(
        task_type="intelligence",
        provider="claude", model="claude-sonnet-4-6",
        fallback_provider="claude", fallback_model="claude-haiku-4-5-20251001",
        max_tokens=2048, temperature=0.3, timeout_seconds=30,
    ),
    PolicyRule(
        task_type="creative",
        provider="claude", model="claude-sonnet-4-6",
        fallback_provider="openai", fallback_model="gpt-4o-mini",
        max_tokens=2048, temperature=0.8, timeout_seconds=30,
    ),
    PolicyRule(
        task_type="strategic_planning",
        provider="claude", model="claude-sonnet-4-6",
        fallback_provider="claude", fallback_model="claude-haiku-4-5-20251001",
        max_tokens=2048, temperature=0.5, timeout_seconds=30,
    ),
    PolicyRule(
        task_type="persona",
        provider="claude", model="claude-haiku-4-5-20251001",
        fallback_provider="claude", fallback_model="claude-haiku-4-5-20251001",
        max_tokens=1024, temperature=0.7, timeout_seconds=20,
    ),
    PolicyRule(
        task_type="revenue",
        provider="claude", model="claude-haiku-4-5-20251001",
        fallback_provider="claude", fallback_model="claude-haiku-4-5-20251001",
        max_tokens=1024, temperature=0.3, timeout_seconds=20,
    ),
    PolicyRule(
        task_type="learning",
        provider="claude", model="claude-haiku-4-5-20251001",
        fallback_provider="claude", fallback_model="claude-haiku-4-5-20251001",
        max_tokens=1024, temperature=0.5, timeout_seconds=20,
    ),
    PolicyRule(
        task_type="routing",
        provider="claude", model="claude-haiku-4-5-20251001",
        fallback_provider="claude", fallback_model="claude-haiku-4-5-20251001",
        max_tokens=512, temperature=0.1, timeout_seconds=15,
    ),
    PolicyRule(
        task_type="summary",
        provider="claude", model="claude-haiku-4-5-20251001",
        fallback_provider="gemini", fallback_model="gemini-1.5-flash",
        max_tokens=512, temperature=0.5, timeout_seconds=20,
    ),
    PolicyRule(
        task_type="default",
        provider="claude", model="claude-sonnet-4-6",
        fallback_provider="claude", fallback_model="claude-haiku-4-5-20251001",
        max_tokens=2048, temperature=0.7, timeout_seconds=30,
    ),
]

# Env override: performance profiles
_OPENAI_PRIMARY_OVERRIDES = {
    "editorial": PolicyRule(
        task_type="editorial",
        provider="openai", model="gpt-4o",
        fallback_provider="claude", fallback_model="claude-sonnet-4-6",
        max_tokens=4096, temperature=0.7, timeout_seconds=30,
    ),
    "creative": PolicyRule(
        task_type="creative",
        provider="openai", model="gpt-4o",
        fallback_provider="claude", fallback_model="claude-sonnet-4-6",
        max_tokens=2048, temperature=0.8, timeout_seconds=30,
    ),
}

_COST_OPTIMIZED_OVERRIDES = {
    "executive": PolicyRule(
        task_type="executive",
        provider="claude", model="claude-sonnet-4-6",
        fallback_provider="claude", fallback_model="claude-haiku-4-5-20251001",
        max_tokens=1024, temperature=0.3, timeout_seconds=30,
    ),
    "editorial": PolicyRule(
        task_type="editorial",
        provider="claude", model="claude-haiku-4-5-20251001",
        fallback_provider="openai", fallback_model="gpt-4o-mini",
        max_tokens=2048, temperature=0.7, timeout_seconds=20,
    ),
    "creative": PolicyRule(
        task_type="creative",
        provider="claude", model="claude-haiku-4-5-20251001",
        fallback_provider="openai", fallback_model="gpt-4o-mini",
        max_tokens=1024, temperature=0.8, timeout_seconds=20,
    ),
}

_PERFORMANCE_OVERRIDES = {
    "editorial": PolicyRule(
        task_type="editorial",
        provider="claude", model="claude-opus-4-8",
        fallback_provider="openai", fallback_model="gpt-4o",
        max_tokens=4096, temperature=0.7, timeout_seconds=60,
    ),
    "intelligence": PolicyRule(
        task_type="intelligence",
        provider="claude", model="claude-opus-4-8",
        fallback_provider="claude", fallback_model="claude-sonnet-4-6",
        max_tokens=2048, temperature=0.3, timeout_seconds=60,
    ),
}


class ModelPolicy:
    """Loads policy from environment + config; selects model per request."""

    def __init__(self) -> None:
        self._rules: dict[str, PolicyRule] = {r.task_type: r for r in _DEFAULT_RULES}
        self._apply_env_overrides()

    def _apply_env_overrides(self) -> None:
        policy_name = os.environ.get("DEFAULT_MODEL_POLICY", "claude_primary")
        if policy_name == "openai_primary":
            self._rules.update(_OPENAI_PRIMARY_OVERRIDES)
            logger.info("[ModelPolicy] Applying openai_primary overrides")
        elif policy_name == "cost_optimized":
            self._rules.update(_COST_OPTIMIZED_OVERRIDES)
            logger.info("[ModelPolicy] Applying cost_optimized overrides")
        elif policy_name == "performance":
            self._rules.update(_PERFORMANCE_OVERRIDES)
            logger.info("[ModelPolicy] Applying performance overrides")
        # "claude_primary" is the default — no changes needed

    def select(self, request: ModelRequest) -> PolicyRule:
        """Return the policy rule for this request."""
        rule = self._rules.get(request.task_type)
        if rule is None:
            rule = self._rules["default"]
            logger.debug(
                "[ModelPolicy] No rule for task_type=%s — using default",
                request.task_type,
            )
        return rule
