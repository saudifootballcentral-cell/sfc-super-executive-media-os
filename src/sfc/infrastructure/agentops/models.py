"""Models for the AgentOps infrastructure service."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AgentOpsConfig(BaseModel):
    """Configuration for the AgentOps service."""

    target_cost_per_run_usd: float = 0.10
    max_cost_per_run_usd: float = 1.0
    max_error_rate: float = 0.05
    uptime_slo: float = 99.9
    p95_latency_ms: float = 5000.0
    enable_audit: bool = True
    enable_cost_tracking: bool = True
    alert_thresholds: dict[str, float] = Field(
        default_factory=lambda: {
            "cost_usd": 1.0,
            "error_rate": 0.05,
            "latency_p95_ms": 5000.0,
        }
    )
