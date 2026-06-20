"""Models for the Capability Registry infrastructure service."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CapabilityUsageReport(BaseModel):
    """Usage report for a single capability."""

    capability_id: str
    name: str
    category: str
    provider: str
    call_count: int
    status: str
    cost_per_call_usd: float
    total_cost_usd: float


class CapabilityRegistryReport(BaseModel):
    """Full capability registry report."""

    total_capabilities: int
    active_capabilities: int
    by_category: dict[str, int] = Field(default_factory=dict)
    by_provider: dict[str, int] = Field(default_factory=dict)
    top_used: list[CapabilityUsageReport] = Field(default_factory=list)
    unavailable: list[str] = Field(default_factory=list)
