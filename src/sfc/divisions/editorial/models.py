"""Editorial Division — Pydantic models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from sfc.divisions.base import DivisionInput, DivisionOutput


class EditorialState(BaseModel):
    """Current in-flight state for the Editorial division."""

    active_run_id: str | None = None
    drafts_in_progress: int = 0
    last_publish_at: datetime | None = None


class EditorialInput(DivisionInput):
    """Editorial-specific input."""

    content_types: list[str] = Field(default_factory=list)
    target_platforms: list[str] = Field(default_factory=list)


class EditorialOutput(DivisionOutput):
    """Editorial-specific output."""

    content_drafts: list[dict[str, Any]] = Field(default_factory=list)


class EditorialMetrics(BaseModel):
    """KPIs tracked by the Editorial division."""

    total_drafts_produced: int = 0
    avg_draft_quality_score: float = 0.0
    accuracy_check_pass_rate: float = 0.0
    avg_word_count: float = 0.0


class EditorialMemoryReference(BaseModel):
    """Memory pointers for editorial artifacts."""

    drafts_key: str = ""
    brief_key: str = ""
    run_id: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
