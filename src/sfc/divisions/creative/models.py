"""Creative Division — Pydantic models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from sfc.divisions.base import DivisionInput, DivisionOutput


class CreativeState(BaseModel):
    active_run_id: str | None = None
    assets_in_production: int = 0
    last_provider_call: datetime | None = None


class CreativeInput(DivisionInput):
    target_platforms: list[str] = Field(default_factory=list)


class CreativeOutput(DivisionOutput):
    creative_assets: list[dict[str, Any]] = Field(default_factory=list)


class CreativeMetrics(BaseModel):
    total_assets_produced: int = 0
    avg_production_time_hours: float = 0.0
    provider_usage: dict[str, int] = Field(default_factory=dict)


class CreativeMemoryReference(BaseModel):
    assets_key: str = ""
    run_id: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
