"""Clip enhancement models — aspect ratio variants and platform-specific cuts."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class AspectRatio(str, Enum):
    LANDSCAPE_16_9 = "16:9"
    PORTRAIT_9_16 = "9:16"
    SQUARE_1_1 = "1:1"


class EnhancedClipVariant(BaseModel):
    variant_id: str = Field(default_factory=lambda: str(uuid4()))
    clip_id: str
    platform: str
    aspect_ratio: AspectRatio
    local_path: str = ""
    public_url: str = ""
    duration_seconds: float = 0.0
    file_size_bytes: int = 0
    has_subtitles: bool = False
    has_intro: bool = False
    has_outro: bool = False
    ready: bool = False
    metadata: dict = Field(default_factory=dict)

    model_config = {"frozen": False}


class EnhancementResult(BaseModel):
    enhancement_id: str = Field(default_factory=lambda: str(uuid4()))
    clip_id: str
    variants: list[EnhancedClipVariant] = Field(default_factory=list)
    dry_run: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}

    @property
    def ready_variants(self) -> list[EnhancedClipVariant]:
        return [v for v in self.variants if v.ready]
