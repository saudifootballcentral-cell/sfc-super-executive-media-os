"""GeneratedAsset — real file-backed creative asset with full provenance."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class GeneratedAssetStatus(str, Enum):
    GENERATED = "generated"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    FAILED = "failed"
    REJECTED = "rejected"
    PENDING_REVIEW = "pending_review"


class GovernanceStatus(str, Enum):
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class GeneratedAsset(BaseModel):
    asset_id: str = Field(default_factory=lambda: str(uuid4()))
    asset_type: str  # image | thumbnail | audio
    provider: str = ""
    status: GeneratedAssetStatus = GeneratedAssetStatus.PROVIDER_UNAVAILABLE
    local_path: str = ""
    public_url: str | None = None
    mime_type: str = ""
    file_size: int = 0
    checksum_sha256: str = ""
    prompt: str = ""
    negative_prompt: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    cost_estimate: float = 0.0
    quality_score: float = 0.0
    governance_status: GovernanceStatus = GovernanceStatus.PENDING_REVIEW
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"frozen": False}

    @property
    def is_publishable(self) -> bool:
        if self.status != GeneratedAssetStatus.GENERATED:
            return False
        if not self.local_path:
            return False
        if not Path(self.local_path).exists():
            return False
        if self.file_size <= 0:
            return False
        if not self.checksum_sha256:
            return False
        if self.governance_status not in (
            GovernanceStatus.APPROVED,
            GovernanceStatus.PENDING_REVIEW,
        ):
            return False
        return True

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def to_summary(self) -> str:
        return (
            f"[{self.asset_type}] provider={self.provider} "
            f"status={self.status.value} size={self.file_size}B "
            f"quality={self.quality_score:.0f}"
        )
