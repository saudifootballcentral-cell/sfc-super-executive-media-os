from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class GovernanceCheckType(str, Enum):
    PROMPT_VALIDATION = "prompt_validation"
    CAPABILITY_VALIDATION = "capability_validation"
    PERFORMANCE_VALIDATION = "performance_validation"
    RISK_ASSESSMENT = "risk_assessment"
    COMPLIANCE_REVIEW = "compliance_review"


class GovernanceCheck(BaseModel):
    check_type: GovernanceCheckType
    passed: bool
    score: float
    notes: str = ""


class GovernanceReport(BaseModel):
    report_id: str = Field(default_factory=lambda: f"GOV-{uuid4().hex[:6].upper()}")
    persona_id: str
    checks: list[GovernanceCheck]
    overall_passed: bool
    risk_score: float
    compliance_notes: list[str]
    reviewed_at: datetime = Field(default_factory=datetime.utcnow)
    reviewer: str = "governance_framework"


class ApprovalRecord(BaseModel):
    approval_id: str = Field(default_factory=lambda: f"APPR-{uuid4().hex[:6].upper()}")
    persona_id: str
    approved: bool
    approver: str
    rationale: str
    approved_at: datetime = Field(default_factory=datetime.utcnow)
