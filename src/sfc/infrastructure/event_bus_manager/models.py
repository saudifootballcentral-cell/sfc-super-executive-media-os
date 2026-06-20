"""Models for the Event Bus Manager infrastructure service."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class EventFilter(BaseModel):
    """Filter criteria for querying the event log."""

    event_type: str | None = None
    run_id: str | None = None
    priority: str | None = None
    division: str | None = None
    since: datetime | None = None
    limit: int = 100


class EventSummary(BaseModel):
    """Summary statistics for the event bus."""

    total_events: int = 0
    by_type: dict[str, int] = Field(default_factory=dict)
    by_priority: dict[str, int] = Field(default_factory=dict)
    dlq_size: int = 0
    active_workflows: int = 0
    recent_events: list[dict[str, Any]] = Field(default_factory=list)
