"""Breaking News Command Center — Pydantic models."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class NewsUrgency(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class VerificationStatus(str, Enum):
    UNVERIFIED = "unverified"
    PARTIAL = "partial"
    VERIFIED = "verified"
    PUBLISHED = "published"


class SourceValidation(BaseModel):
    source_name: str
    reliability_score: float
    verified: bool
    validated_at: datetime = Field(default_factory=datetime.utcnow)


class BreakingNewsAlert(BaseModel):
    alert_id: str = Field(default_factory=lambda: str(uuid4()))
    headline: str
    urgency: NewsUrgency
    sources: list[SourceValidation] = Field(default_factory=list)
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    confidence_score: float = 0.0
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    published: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class NewsPackage(BaseModel):
    alert_id: str
    thread_package: list[str] = Field(default_factory=list)
    article_draft: str = ""
    video_brief: str = ""
    distribution_plan: dict[str, Any] = Field(default_factory=dict)
    executive_brief: str = ""
