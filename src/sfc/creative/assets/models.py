"""Creative Asset Management models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class AssetType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    THUMBNAIL = "thumbnail"
    SCRIPT = "script"
    STORYBOARD = "storyboard"
    SHORTS_PACKAGE = "shorts_package"
    PODCAST_EPISODE = "podcast_episode"
    CONTENT_PACKAGE = "content_package"


class AssetStatus(str, Enum):
    PENDING = "pending"
    GENERATING = "generating"
    GENERATED = "generated"
    QC_PENDING = "qc_pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"


class CreativeAsset(BaseModel):
    asset_id: str = Field(default_factory=lambda: str(uuid4()))
    asset_type: AssetType
    status: AssetStatus = AssetStatus.GENERATED
    title: str
    description: str = ""
    platform: str = ""
    file_url: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    quality_score: float = 0.0
    brand_alignment_score: float = 0.0
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    source_asset_id: str = ""

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def to_summary(self) -> str:
        return (
            f"[{self.asset_type.value}] '{self.title}' [{self.status.value}] — "
            f"quality: {self.quality_score:.0f}/100, "
            f"brand: {self.brand_alignment_score:.0f}/100."
        )


class AssetRegistryReport(BaseModel):
    registry_id: str = Field(default_factory=lambda: str(uuid4()))
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    assets: list[CreativeAsset] = Field(default_factory=list)
    total_assets: int = 0
    assets_by_type: dict[str, int] = Field(default_factory=dict)
    assets_by_status: dict[str, int] = Field(default_factory=dict)
    avg_quality_score: float = 0.0
    approved_count: int = 0
    rejected_count: int = 0

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
