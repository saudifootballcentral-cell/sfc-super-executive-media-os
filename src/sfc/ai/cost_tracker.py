"""Cost tracking for all AI calls across the SFC pipeline."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger("sfc.ai.cost_tracker")

# Cost per 1M tokens (input / output) in USD
_INPUT_COST_PER_1M: dict[str, float] = {
    "claude-opus-4-8": 15.0,
    "claude-sonnet-4-6": 3.0,
    "claude-haiku-4-5-20251001": 0.25,
    "gpt-4o": 5.0,
    "gpt-4o-mini": 0.15,
    "gemini-1.5-flash": 0.075,
    "gemini-1.5-pro": 3.50,
}

_OUTPUT_COST_PER_1M: dict[str, float] = {
    "claude-opus-4-8": 75.0,
    "claude-sonnet-4-6": 15.0,
    "claude-haiku-4-5-20251001": 1.25,
    "gpt-4o": 15.0,
    "gpt-4o-mini": 0.60,
    "gemini-1.5-flash": 0.30,
    "gemini-1.5-pro": 10.50,
}

_DEFAULT_MAX_DAILY_COST = 100.0


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate cost in USD for a given model and token counts."""
    in_rate = _INPUT_COST_PER_1M.get(model, 3.0)
    out_rate = _OUTPUT_COST_PER_1M.get(model, 15.0)
    return round(
        (in_rate * input_tokens / 1_000_000) + (out_rate * output_tokens / 1_000_000),
        8,
    )


@dataclass
class CallRecord:
    timestamp: str
    task_type: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: int
    success: bool
    used_fallback: bool
    validation_failed: bool


class CostTracker:
    """Tracks AI costs; enforces MAX_DAILY_AI_COST limit."""

    def __init__(self) -> None:
        self._records: list[CallRecord] = []

    def record(self, record: CallRecord) -> None:
        self._records.append(record)
        logger.debug(
            "[CostTracker] %s/%s | $%.6f | success=%s",
            record.provider,
            record.model,
            record.cost_usd,
            record.success,
        )

    def get_session_total_usd(self) -> float:
        return round(sum(r.cost_usd for r in self._records), 6)

    def get_model_breakdown(self) -> dict[str, float]:
        breakdown: dict[str, float] = {}
        for r in self._records:
            breakdown[r.model] = round(breakdown.get(r.model, 0.0) + r.cost_usd, 8)
        return breakdown

    def check_budget(self) -> bool:
        """Return True if within MAX_DAILY_AI_COST budget."""
        max_cost = float(os.environ.get("MAX_DAILY_AI_COST", _DEFAULT_MAX_DAILY_COST))
        return self.get_session_total_usd() <= max_cost

    def get_report(self) -> dict[str, Any]:
        total = self.get_session_total_usd()
        model_breakdown = self.get_model_breakdown()
        success_count = sum(1 for r in self._records if r.success)
        fallback_count = sum(1 for r in self._records if r.used_fallback)
        validation_failures = sum(1 for r in self._records if r.validation_failed)
        return {
            "total_calls": len(self._records),
            "successful_calls": success_count,
            "fallback_calls": fallback_count,
            "validation_failures": validation_failures,
            "session_total_usd": total,
            "model_breakdown_usd": model_breakdown,
            "within_budget": self.check_budget(),
            "max_daily_cost_usd": float(os.environ.get("MAX_DAILY_AI_COST", _DEFAULT_MAX_DAILY_COST)),
        }


# Process-level singleton
_instance: CostTracker | None = None


def get_cost_tracker() -> CostTracker:
    """Return process-level singleton CostTracker."""
    global _instance
    if _instance is None:
        _instance = CostTracker()
    return _instance
