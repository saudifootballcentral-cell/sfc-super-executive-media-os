"""Escalation Framework — Pydantic models."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class EscalationLevel(str, Enum):
    L1_OPERATIONAL = "l1_operational"
    L2_STRATEGIC = "l2_strategic"
    L3_EXECUTIVE = "l3_executive"
    L4_CRITICAL = "l4_critical"


class EscalationTrigger(str, Enum):
    LOW_CONFIDENCE = "low_confidence"
    HIGH_RISK = "high_risk"
    COMPLIANCE_RISK = "compliance_risk"
    BRAND_RISK = "brand_risk"
    SECURITY_RISK = "security_risk"
    REVENUE_RISK = "revenue_risk"
    SYSTEM_FAILURE = "system_failure"
    CRITICAL_EVENT = "critical_event"


class EscalationRecord(BaseModel):
    escalation_id: str = Field(default_factory=lambda: str(uuid4()))
    trigger: EscalationTrigger
    level: EscalationLevel
    title: str
    description: str
    context: dict[str, Any] = Field(default_factory=dict)
    raised_at: datetime = Field(default_factory=datetime.utcnow)
    resolved: bool = False
    resolved_at: datetime | None = None
    resolution: str = ""
    decision_required: bool = False


class EscalationReport(BaseModel):
    report_id: str = Field(default_factory=lambda: str(uuid4()))
    period: str
    total_escalations: int = 0
    by_level: dict[str, int] = Field(default_factory=dict)
    by_trigger: dict[str, int] = Field(default_factory=dict)
    avg_resolution_time_minutes: float = 0.0
    open_escalations: list[EscalationRecord] = Field(default_factory=list)
