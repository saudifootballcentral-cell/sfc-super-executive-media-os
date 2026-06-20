"""Models for the Tool Orchestration infrastructure service."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ToolCallRecord(BaseModel):
    """Record of a tool call outcome."""

    provider_id: str
    capability: str
    success: bool
    latency_ms: float
    cost_usd: float
    timestamp: str


class ProviderStats(BaseModel):
    """Aggregated stats for a provider."""

    provider_id: str
    total_calls: int = 0
    success_calls: int = 0
    total_cost_usd: float = 0.0
    avg_latency_ms: float = 0.0
    success_rate: float = 1.0
