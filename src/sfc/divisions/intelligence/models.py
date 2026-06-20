"""Intelligence Division — Pydantic models."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from sfc.divisions.base import DivisionInput, DivisionOutput


class IntelligenceState(BaseModel):
    """Current in-flight state for the Intelligence division."""

    active_run_id: str | None = None
    last_trend_check: datetime | None = None
    monitored_entities: list[str] = Field(default_factory=list)
    source_cache: dict[str, Any] = Field(default_factory=dict)


class IntelligenceInput(DivisionInput):
    """Intelligence-specific input with optional search overrides."""

    topic: str = ""
    force_sources: list[str] = Field(default_factory=list)
    min_sources: int = 2


class IntelligenceOutput(DivisionOutput):
    """Intelligence-specific output."""

    intelligence_report: dict[str, Any] = Field(default_factory=dict)
    verified_sources: list[dict[str, Any]] = Field(default_factory=list)


class IntelligenceMetrics(BaseModel):
    """KPIs tracked by the Intelligence division."""

    total_stories_processed: int = 0
    avg_confidence_score: float = 0.0
    rumor_detection_rate: float = 0.0
    avg_sources_per_story: float = 0.0
    source_verification_pass_rate: float = 0.0


class IntelligenceMemoryReference(BaseModel):
    """Memory pointers for intelligence artifacts."""

    report_key: str = ""
    sources_key: str = ""
    trend_snapshot_key: str = ""
    entity_cache_key: str = ""
    run_id: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
