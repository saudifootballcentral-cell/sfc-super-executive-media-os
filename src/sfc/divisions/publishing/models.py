"""Publishing Division — Pydantic models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from sfc.divisions.base import DivisionInput, DivisionOutput


class PublishingState(BaseModel):
    active_run_id: str | None = None
    queued_jobs: int = 0
    last_publish_at: datetime | None = None


class PublishingInput(DivisionInput):
    pass


class PublishingOutput(DivisionOutput):
    publish_queue: list[dict[str, Any]] = Field(default_factory=list)
    publish_results: dict[str, Any] = Field(default_factory=dict)


class PublishingMetrics(BaseModel):
    total_published: int = 0
    total_failed: int = 0
    avg_time_to_publish_s: float = 0.0
    platform_coverage: dict[str, int] = Field(default_factory=dict)


class PublishingMemoryReference(BaseModel):
    queue_key: str = ""
    results_key: str = ""
    run_id: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
