"""Resource Allocation models for War Rooms."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field


class ResourceProfile(BaseModel):
    divisions: list[str]
    capabilities: list[str]
    memory_namespace: str
    priority_slots: int
    cost_budget_usd: float = 10.0


class AllocationPlan(BaseModel):
    plan_id: str = Field(default_factory=lambda: f"ALLOC-{uuid4().hex[:6].upper()}")
    war_room_id: str
    resources: ResourceProfile
    conflict_resolutions: list[str] = []
    warnings: list[str] = []
    allocated_at: datetime = Field(default_factory=datetime.utcnow)


class ResourceUtilization(BaseModel):
    total_slots: int = 10
    used_slots: int = 0
    division_utilization: dict[str, float] = {}
    budget_used_usd: float = 0.0
    budget_remaining_usd: float = 0.0
