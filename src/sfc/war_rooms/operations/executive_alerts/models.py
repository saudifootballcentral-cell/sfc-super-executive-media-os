"""Executive Alert System — Pydantic models."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class AlertCategory(str, Enum):
    BREAKING_NEWS = "breaking_news"
    CRISIS = "crisis"
    MAJOR_OPPORTUNITY = "major_opportunity"
    REVENUE_OPPORTUNITY = "revenue_opportunity"
    SYSTEM_FAILURE = "system_failure"
    SECURITY_INCIDENT = "security_incident"
    GOVERNANCE_FAILURE = "governance_failure"
    EXECUTIVE_SUMMARY = "executive_summary"


class AlertSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ExecutiveAlert(BaseModel):
    alert_id: str = Field(default_factory=lambda: str(uuid4()))
    category: AlertCategory
    severity: AlertSeverity
    title: str
    summary: str
    action_required: bool = False
    recommended_action: str = ""
    context: dict[str, Any] = Field(default_factory=dict)
    raised_at: datetime = Field(default_factory=datetime.utcnow)
    acknowledged: bool = False
    acknowledged_at: datetime | None = None


class ExecutiveSummary(BaseModel):
    summary_id: str = Field(default_factory=lambda: str(uuid4()))
    period: str
    headline: str
    key_points: list[str] = Field(default_factory=list)
    decisions_required: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
