"""Strategic Planning Division — Pydantic models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from sfc.divisions.base import DivisionInput, DivisionOutput


class StrategicPlanningState(BaseModel):
    active_run_id: str | None = None
    current_quarter: int = 1
    active_plan_id: str | None = None
    last_cycle_at: datetime | None = None


class StrategicPlanningInput(DivisionInput):
    vision: str = ""
    budget_usd: float = 0.0


class StrategicPlanningOutput(DivisionOutput):
    execution_plan: dict[str, Any] = Field(default_factory=dict)
    weekly_missions: list[dict[str, Any]] = Field(default_factory=list)
    prioritized_items: list[dict[str, Any]] = Field(default_factory=list)


class StrategicPlanningMetrics(BaseModel):
    plans_created: int = 0
    missions_generated: int = 0
    items_prioritized: int = 0
    avg_ice_score: float = 0.0


class StrategicPlanningMemoryReference(BaseModel):
    plan_key: str = ""
    mission_key: str = ""
    run_id: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
