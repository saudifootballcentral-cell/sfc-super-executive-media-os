"""Clip governance models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class ClipGovernanceStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_MANUAL_REVIEW = "needs_manual_review"
    RIGHTS_BLOCKED = "rights_blocked"


class ClipGovernanceResult(BaseModel):
    governance_id: str = Field(default_factory=lambda: str(uuid4()))
    clip_id: str
    package_id: str = ""
    status: ClipGovernanceStatus = ClipGovernanceStatus.PENDING
    rights_verified: bool = False
    brand_safe: bool = True
    content_policy_compliant: bool = True
    quality_gate_passed: bool = False
    issues: list[str] = Field(default_factory=list)
    reviewer: str = "automated"
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}

    @property
    def cleared_for_publishing(self) -> bool:
        return self.status in (
            ClipGovernanceStatus.APPROVED,
            ClipGovernanceStatus.NEEDS_MANUAL_REVIEW,
        ) and self.rights_verified and self.brand_safe and self.content_policy_compliant
