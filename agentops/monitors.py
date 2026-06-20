"""AgentOps Monitors — Health, Cost, and Quality monitoring."""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from datetime import datetime
from typing import Any
from uuid import UUID

logger = logging.getLogger("sfc.agentops.monitors")

COST_PROVIDERS = [
    "claude",
    "openai",
    "gemini",
    "veo",
    "kling",
    "runway",
    "luma",
    "elevenlabs",
]


class HealthMonitor:
    """Tracks agent and tool health: failures, timeouts, latency, availability, recovery."""

    def __init__(self) -> None:
        self._records: dict[str, dict[str, Any]] = defaultdict(lambda: {
            "failures": 0,
            "timeouts": 0,
            "total_calls": 0,
            "total_latency_ms": 0.0,
            "last_failure": None,
            "last_recovery": None,
        })

    def record_call(self, component_id: str, latency_ms: float, success: bool, timeout: bool = False) -> None:
        r = self._records[component_id]
        r["total_calls"] += 1
        r["total_latency_ms"] += latency_ms
        if not success:
            r["failures"] += 1
            r["last_failure"] = datetime.utcnow().isoformat()
        if timeout:
            r["timeouts"] += 1
        if not success and r["failures"] > 1:
            r["last_recovery"] = None
        logger.debug("[HealthMonitor] %s — success=%s latency=%.1fms", component_id, success, latency_ms)

    def mark_recovered(self, component_id: str) -> None:
        self._records[component_id]["last_recovery"] = datetime.utcnow().isoformat()

    def health_score(self, component_id: str) -> float:
        r = self._records.get(component_id, {})
        total = r.get("total_calls", 0)
        if total == 0:
            return 100.0
        failures = r.get("failures", 0)
        return max(0.0, 100.0 * (1 - failures / total))

    def avg_latency_ms(self, component_id: str) -> float:
        r = self._records.get(component_id, {})
        total = r.get("total_calls", 0)
        if total == 0:
            return 0.0
        return r.get("total_latency_ms", 0.0) / total

    def availability(self, component_id: str) -> float:
        return self.health_score(component_id)

    def summary(self, component_id: str) -> dict[str, Any]:
        return {
            "component_id": component_id,
            "health_score": self.health_score(component_id),
            "avg_latency_ms": self.avg_latency_ms(component_id),
            **self._records.get(component_id, {}),
        }


class CostMonitor:
    """Tracks API costs per provider."""

    def __init__(self) -> None:
        self._costs: dict[str, float] = {p: 0.0 for p in COST_PROVIDERS}
        self._call_counts: dict[str, int] = {p: 0 for p in COST_PROVIDERS}

    def record_cost(self, provider: str, cost: float) -> None:
        provider = provider.lower()
        if provider not in self._costs:
            self._costs[provider] = 0.0
            self._call_counts[provider] = 0
        self._costs[provider] += cost
        self._call_counts[provider] += 1
        logger.debug("[CostMonitor] %s += $%.4f (total=$%.4f)", provider, cost, self._costs[provider])

    def total_cost(self) -> float:
        return sum(self._costs.values())

    def cost_by_provider(self) -> dict[str, float]:
        return dict(self._costs)

    def report(self) -> dict[str, Any]:
        return {
            "total_cost_usd": self.total_cost(),
            "by_provider": self.cost_by_provider(),
            "call_counts": dict(self._call_counts),
        }


class QualityMonitor:
    """Tracks content quality: hallucination rate, approval rate, publishing success."""

    def __init__(self) -> None:
        self._hallucinations = 0
        self._total_outputs = 0
        self._approvals = 0
        self._rejections = 0
        self._publish_successes = 0
        self._publish_failures = 0
        self._performance_scores: list[float] = []

    def record_output(self, approved: bool, hallucination_detected: bool = False) -> None:
        self._total_outputs += 1
        if hallucination_detected:
            self._hallucinations += 1
            logger.warning("[QualityMonitor] Hallucination detected — total=%d", self._hallucinations)
        if approved:
            self._approvals += 1
        else:
            self._rejections += 1

    def record_publish(self, success: bool) -> None:
        if success:
            self._publish_successes += 1
        else:
            self._publish_failures += 1

    def record_performance(self, score: float) -> None:
        self._performance_scores.append(score)

    @property
    def hallucination_rate(self) -> float:
        if self._total_outputs == 0:
            return 0.0
        return self._hallucinations / self._total_outputs

    @property
    def approval_rate(self) -> float:
        total = self._approvals + self._rejections
        if total == 0:
            return 0.0
        return self._approvals / total

    @property
    def publish_success_rate(self) -> float:
        total = self._publish_successes + self._publish_failures
        if total == 0:
            return 0.0
        return self._publish_successes / total

    @property
    def avg_content_performance(self) -> float:
        if not self._performance_scores:
            return 0.0
        return sum(self._performance_scores) / len(self._performance_scores)

    def report(self) -> dict[str, Any]:
        return {
            "hallucination_rate": self.hallucination_rate,
            "approval_rate": self.approval_rate,
            "publish_success_rate": self.publish_success_rate,
            "avg_content_performance": self.avg_content_performance,
            "total_outputs": self._total_outputs,
        }
