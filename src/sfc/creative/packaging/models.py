"""Content Packaging Engine models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class PackageType(str, Enum):
    X_THREAD = "x_thread"
    YOUTUBE_SHORT = "youtube_short"
    YOUTUBE_VIDEO = "youtube_video"
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    PODCAST = "podcast"


class PublishingMetadata(BaseModel):
    platform: str = ""
    scheduled_at: datetime | None = None
    target_audience: str = ""
    boost_budget_usd: float = 0.0
    geo_targeting: list[str] = Field(default_factory=list)
    language: str = "arabic"
    requires_approval: bool = True
    category: str = ""

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class ContentPackage(BaseModel):
    package_id: str = Field(default_factory=lambda: str(uuid4()))
    package_type: PackageType
    title: str
    description: str = ""
    caption: str = ""
    hashtags: list[str] = Field(default_factory=list)
    thumbnail_url: str = ""
    media_asset_ids: list[str] = Field(default_factory=list)
    media_assets: list[dict[str, Any]] = Field(default_factory=list)
    publishing_metadata: PublishingMetadata = Field(default_factory=PublishingMetadata)
    quality_score: float = 0.0
    ready_to_publish: bool = False
    governance_cleared: bool = False
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def to_summary(self) -> str:
        ready = "READY" if self.ready_to_publish else "PENDING"
        return (
            f"[{self.package_type.value.upper()}] '{self.title}' [{ready}] — "
            f"quality: {self.quality_score:.0f}/100, "
            f"{len(self.hashtags)} hashtags."
        )


class PackagingReport(BaseModel):
    report_id: str = Field(default_factory=lambda: str(uuid4()))
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    packages: list[ContentPackage] = Field(default_factory=list)
    total_packages: int = 0
    ready_to_publish: int = 0
    packages_by_type: dict[str, int] = Field(default_factory=dict)
    avg_quality_score: float = 0.0

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
