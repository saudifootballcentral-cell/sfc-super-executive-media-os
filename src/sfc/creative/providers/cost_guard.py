"""CostGuard — per-run and daily generation budget enforcement."""

from __future__ import annotations

import logging
import os
from datetime import date
from typing import Any

logger = logging.getLogger("sfc.creative.providers.cost")

# Default cost estimates per provider call (USD)
PROVIDER_COST_ESTIMATES: dict[str, float] = {
    "openai_image": 0.04,
    "flux": 0.003,
    "ideogram": 0.08,
    "elevenlabs": 0.01,
    "azure_voice": 0.005,
}

_singleton: "CostGuard | None" = None


def get_cost_guard() -> "CostGuard":
    global _singleton
    if _singleton is None:
        _singleton = CostGuard()
    return _singleton


class CostGuard:
    """Enforces per-run and daily budgets before any provider call."""

    def __init__(self) -> None:
        self._run_costs: dict[str, float] = {}    # run_id → USD
        self._daily_costs: dict[str, float] = {}   # YYYY-MM-DD → USD
        self._asset_log: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Feature flags
    # ------------------------------------------------------------------

    def is_generation_enabled(self) -> bool:
        """True only when GENERATE_REAL_ASSETS=true in environment."""
        return os.environ.get("GENERATE_REAL_ASSETS", "false").lower() == "true"

    def is_dry_run_creative(self) -> bool:
        return os.environ.get("DRY_RUN_CREATIVE", "true").lower() == "true"

    # ------------------------------------------------------------------
    # Budget checks
    # ------------------------------------------------------------------

    def can_afford(
        self,
        provider: str,
        run_id: str | None = None,
        per_run_limit: float | None = None,
        daily_limit: float | None = None,
    ) -> bool:
        """Return True if calling provider stays within budget."""
        if not self.is_generation_enabled():
            return False

        cost = PROVIDER_COST_ESTIMATES.get(provider, 0.0)
        run_limit = per_run_limit or float(
            os.environ.get("CREATIVE_PER_RUN_BUDGET_USD", "5.0")
        )
        day_limit = daily_limit or float(
            os.environ.get("CREATIVE_DAILY_BUDGET_USD", "50.0")
        )

        if run_id:
            run_total = self._run_costs.get(run_id, 0.0)
            if run_total + cost > run_limit:
                logger.warning(
                    "[CostGuard] Per-run budget exceeded | run=%s limit=%.2f current=%.4f cost=%.4f",
                    run_id,
                    run_limit,
                    run_total,
                    cost,
                )
                return False

        today = date.today().isoformat()
        day_total = self._daily_costs.get(today, 0.0)
        if day_total + cost > day_limit:
            logger.warning(
                "[CostGuard] Daily budget exceeded | date=%s limit=%.2f current=%.4f cost=%.4f",
                today,
                day_limit,
                day_total,
                cost,
            )
            return False

        return True

    # ------------------------------------------------------------------
    # Cost recording
    # ------------------------------------------------------------------

    def record_cost(
        self, asset_id: str, provider: str, run_id: str | None = None
    ) -> None:
        cost = PROVIDER_COST_ESTIMATES.get(provider, 0.0)
        today = date.today().isoformat()
        self._daily_costs[today] = self._daily_costs.get(today, 0.0) + cost
        if run_id:
            self._run_costs[run_id] = self._run_costs.get(run_id, 0.0) + cost
        self._asset_log.append(
            {
                "asset_id": asset_id,
                "provider": provider,
                "cost_usd": cost,
                "date": today,
                "run_id": run_id,
            }
        )
        logger.info(
            "[CostGuard] Recorded | provider=%s cost=%.4f daily_total=%.4f",
            provider,
            cost,
            self._daily_costs[today],
        )

    def estimate_cost(self, provider: str) -> float:
        return PROVIDER_COST_ESTIMATES.get(provider, 0.0)

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def daily_total(self) -> float:
        return self._daily_costs.get(date.today().isoformat(), 0.0)

    def run_total(self, run_id: str) -> float:
        return self._run_costs.get(run_id, 0.0)

    def asset_log(self) -> list[dict[str, Any]]:
        return list(self._asset_log)

    def reset_for_test(self) -> None:
        """Reset all tracking state (test helper)."""
        self._run_costs.clear()
        self._daily_costs.clear()
        self._asset_log.clear()
