"""Crisis Management War Room models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class CrisisType(str, Enum):
    FAKE_NEWS = "fake_news"
    REPUTATION_RISK = "reputation_risk"
    PUBLISHING_ERROR = "publishing_error"
    SPONSOR_CRISIS = "sponsor_crisis"
    SECURITY_INCIDENT = "security_incident"
    PUBLIC_CONTROVERSY = "public_controversy"
    PLATFORM_STRIKE = "platform_strike"


class CrisisSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class CrisisEvent(BaseModel):
    crisis_id: str = Field(default_factory=lambda: f"CRS-{uuid4().hex[:8].upper()}")
    crisis_type: CrisisType
    severity: CrisisSeverity
    description: str
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    detected_by: str = "system"
    affected_content_ids: list[str] = []
    affected_platforms: list[str] = []
    status: str = "open"


class CrisisReport(BaseModel):
    crisis_id: str
    crisis_type: CrisisType
    severity: CrisisSeverity
    description: str
    detected_at: datetime
    initial_assessment: str = ""
    containment_actions: list[str] = []
    damage_assessment: dict[str, Any] = {}
    recovery_plan: list[str] = []
    executive_alert: str = ""
    lessons_learned: list[str] = []
    resolved_at: datetime | None = None
    status: str = "open"
