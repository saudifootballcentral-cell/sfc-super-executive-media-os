"""AgentOps Monitors — Health, Cost, and Quality tracking."""

from __future__ import annotations

import logging
import threading
from collections import defaultdict
from datetime import datetime
from typing import Any

logger = logging.getLogger("sfc.agentops.monitors")

TRACKED_PROVIDERS = ["claude", "openai", "gemini", "veo", "kling", "runway", "luma", "elevenlabs"]


class HealthMonitor:
    def __init__(self) -> None:
        self._records: dict[str, dict[str, Any]] = defaultdict(lambda: {
            "failures": 0, "timeouts": 0, "total_calls": 0,
            "total_latency_ms": 0.0, "last_failure": None,
        })
        self._lock = threading.RLock()

    def record_call(self, component_id: str, latency_ms: float, success: bool, timeout: bool = False) -> None:
        with self._lock:
            r = self._records[component_id]
            r["total_calls"] += 1
            r["total_latency_ms"] += latency_ms
            if not success:
                r["failures"] += 1
                r["last_failure"] = datetime.utcnow().isoformat()
            if timeout:
                r["timeouts"] += 1

    def health_score(self, component_id: str) -> float:
        with self._lock:
            r = self._records.get(component_id, {})
            total = r.get("total_calls", 0)
            if total == 0:
                return 100.0
            return max(0.0, 100.0 * (1 - r.get("failures", 0) / total))

    def avg_latency_ms(self, component_id: str) -> float:
        with self._lock:
            r = self._records.get(component_id, {})
            total = r.get("total_calls", 0)
            return r.get("total_latency_ms", 0.0) / total if total else 0.0


class CostMonitor:
    def __init__(self) -> None:
        self._costs: dict[str, float] = {p: 0.0 for p in TRACKED_PROVIDERS}
        self._call_counts: dict[str, int] = {p: 0 for p in TRACKED_PROVIDERS}
        self._lock = threading.RLock()

    def record_cost(self, provider: str, cost: float) -> None:
        provider = provider.lower()
        with self._lock:
            self._costs.setdefault(provider, 0.0)
            self._call_counts.setdefault(provider, 0)
            self._costs[provider] += cost
            self._call_counts[provider] += 1

    def total_cost(self) -> float:
        with self._lock:
            return sum(self._costs.values())

    def report(self) -> dict[str, Any]:
        with self._lock:
            return {
                "total_cost_usd": sum(self._costs.values()),
                "by_provider": dict(self._costs),
                "call_counts": dict(self._call_counts),
            }


class QualityMonitor:
    def __init__(self) -> None:
        self._hallucinations = 0
        self._total_outputs = 0
        self._approvals = 0
        self._rejections = 0
        self._publish_successes = 0
        self._publish_failures = 0
        self._lock = threading.RLock()

    def record_output(self, approved: bool, hallucination_detected: bool = False) -> None:
        with self._lock:
            self._total_outputs += 1
            if hallucination_detected:
                self._hallucinations += 1
            if approved:
                self._approvals += 1
            else:
                self._rejections += 1

    def record_publish(self, success: bool) -> None:
        with self._lock:
            if success:
                self._publish_successes += 1
            else:
                self._publish_failures += 1

    @property
    def approval_rate(self) -> float:
        with self._lock:
            total = self._approvals + self._rejections
            return self._approvals / total if total else 0.0

    @property
    def hallucination_rate(self) -> float:
        with self._lock:
            return self._hallucinations / self._total_outputs if self._total_outputs else 0.0

    def report(self) -> dict[str, Any]:
        return {
            "total_outputs": self._total_outputs,
            "approval_rate": self.approval_rate,
            "hallucination_rate": self.hallucination_rate,
            "publish_successes": self._publish_successes,
        }
