"""Production Quality Control models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class QualityCheckType(str, Enum):
    BRAND_ALIGNMENT = "brand_alignment"
    VISUAL_QUALITY = "visual_quality"
    NARRATIVE_CONSISTENCY = "narrative_consistency"
    GOVERNANCE_COMPLIANCE = "governance_compliance"
    TECHNICAL_QUALITY = "technical_quality"


class QualityCheckResult(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"


class QualityCheck(BaseModel):
    check_id: str = Field(default_factory=lambda: str(uuid4()))
    check_type: QualityCheckType
    result: QualityCheckResult
    score: float = 0.0
    feedback: str = ""
    issues: list[str] = Field(default_factory=list)

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class QualityReport(BaseModel):
    report_id: str = Field(default_factory=lambda: str(uuid4()))
    asset_id: str = ""
    asset_type: str = ""
    asset_title: str = ""
    checks: list[QualityCheck] = Field(default_factory=list)
    overall_score: float = 0.0
    approved: bool = False
    revision_requests: list[str] = Field(default_factory=list)
    qc_summary: str = ""
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def to_summary(self) -> str:
        status = "APPROVED" if self.approved else "REJECTED"
        return (
            f"QC [{status}] '{self.asset_title}' — "
            f"score: {self.overall_score:.0f}/100, "
            f"{len(self.checks)} checks, {len(self.revision_requests)} revision(s)."
        )


class QualityBatch(BaseModel):
    batch_id: str = Field(default_factory=lambda: str(uuid4()))
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    reports: list[QualityReport] = Field(default_factory=list)
    total_reviewed: int = 0
    total_approved: int = 0
    total_rejected: int = 0
    avg_score: float = 0.0
    pass_rate: float = 0.0

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
