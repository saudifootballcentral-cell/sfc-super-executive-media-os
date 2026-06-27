"""Clip packaging models."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field


class PlatformClipVariant(BaseModel):
    variant_id: str = Field(default_factory=lambda: str(uuid4()))
    platform: str
    aspect_ratio: str = "16:9"
    duration_seconds: float = 0.0
    local_path: str = ""
    public_url: str = ""
    thumbnail_path: str = ""
    caption_path: str = ""
    file_size_bytes: int = 0
    ready_to_publish: bool = False
    metadata: dict = Field(default_factory=dict)

    model_config = {"frozen": False}


class ClipPackage(BaseModel):
    package_id: str = Field(default_factory=lambda: str(uuid4()))
    clip_id: str
    video_id: str
    title: str
    description: str = ""
    clip_type: str = ""
    hashtags: list[str] = Field(default_factory=list)
    variants: list[PlatformClipVariant] = Field(default_factory=list)
    quality_score: float = 0.0
    governance_cleared: bool = False
    published: bool = False
    dry_run: bool = False
    attribution: str = ""                             # credit line propagated from VideoSource
    platform_rights: list[str] = Field(default_factory=list)  # [] = all; non-empty = restricted
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict = Field(default_factory=dict)

    model_config = {"frozen": False}

    @property
    def publishable_variants(self) -> list[PlatformClipVariant]:
        return [v for v in self.variants if v.ready_to_publish]

    @property
    def is_ready(self) -> bool:
        return (
            self.governance_cleared
            and self.quality_score >= 70.0
            and len(self.publishable_variants) > 0
        )
