"""AI Shorts Factory models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ShortsPlatform(str, Enum):
    YOUTUBE_SHORTS = "youtube_shorts"
    TIKTOK = "tiktok"
    INSTAGRAM_REELS = "instagram_reels"


class ShortsScript(BaseModel):
    script_id: str = Field(default_factory=lambda: str(uuid4()))
    hook: str = ""
    body: str = ""
    call_to_action: str = ""
    full_script: str = ""
    word_count: int = 0
    estimated_duration_seconds: float = 0.0

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class ShortsScene(BaseModel):
    scene_number: int = 1
    duration_seconds: float = 3.0
    visual_description: str = ""
    text_overlay: str = ""
    audio_note: str = ""

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class ShortsPackage(BaseModel):
    package_id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    platform: ShortsPlatform
    script: ShortsScript = Field(default_factory=ShortsScript)
    storyboard: list[ShortsScene] = Field(default_factory=list)
    voiceover_plan: str = ""
    visual_plan: str = ""
    thumbnail_url: str = ""
    caption: str = ""
    hashtags: list[str] = Field(default_factory=list)
    duration_seconds: float = 0.0
    music_suggestion: str = ""
    publishing_metadata: dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def to_summary(self) -> str:
        return (
            f"Shorts '{self.title}' [{self.platform.value}] — "
            f"{self.duration_seconds:.0f}s, {len(self.hashtags)} hashtags, "
            f"{len(self.storyboard)} scenes."
        )
