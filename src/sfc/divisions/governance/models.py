"""Governance Division — Pydantic models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from sfc.divisions.base import DivisionInput, DivisionOutput


class GovernanceState(BaseModel):
    active_run_id: str | None = None
    pending_reviews: int = 0
    escalation_queue: list[str] = Field(default_factory=list)


class GovernanceInput(DivisionInput):
    pass


class GovernanceOutput(DivisionOutput):
    governance_reviews: list[dict[str, Any]] = Field(default_factory=list)
    approved_content: list[dict[str, Any]] = Field(default_factory=list)
    rejected_content: list[dict[str, Any]] = Field(default_factory=list)


class GovernanceMetrics(BaseModel):
    total_reviewed: int = 0
    total_approved: int = 0
    total_rejected: int = 0
    total_escalated: int = 0
    pass_rate: float = 0.0


class GovernanceMemoryReference(BaseModel):
    reviews_key: str = ""
    audit_log_key: str = ""
    run_id: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
