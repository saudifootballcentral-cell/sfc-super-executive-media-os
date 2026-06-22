"""AI Video Factory models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class VideoProvider(str, Enum):
    GOOGLE_VEO = "google_veo"
    KLING = "kling"
    RUNWAY = "runway"
    LUMA = "luma"
    PIKA = "pika"


class VideoFormat(str, Enum):
    SHORT = "short"
    REEL = "reel"
    TIKTOK = "tiktok"
    MATCH_STORY = "match_story"
    PLAYER_STORY = "player_story"
    TRANSFER_STORY = "transfer_story"
    DOCUMENTARY_SEGMENT = "documentary_segment"
    NARRATIVE_VIDEO = "narrative_video"


class AspectRatio(str, Enum):
    VERTICAL = "9:16"
    SQUARE = "1:1"
    HORIZONTAL = "16:9"


class StoryboardScene(BaseModel):
    scene_id: int = 1
    duration_seconds: float = 3.0
    visual_description: str = ""
    audio_direction: str = ""
    text_overlay: str = ""
    transition: str = "cut"
    b_roll: str = ""

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class Storyboard(BaseModel):
    storyboard_id: str = Field(default_factory=lambda: str(uuid4()))
    title: str = ""
    total_scenes: int = 0
    total_duration_seconds: float = 0.0
    aspect_ratio: AspectRatio = AspectRatio.VERTICAL
    scenes: list[StoryboardScene] = Field(default_factory=list)
    music_direction: str = ""
    color_grade: str = ""

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class VideoAsset(BaseModel):
    asset_id: str = Field(default_factory=lambda: str(uuid4()))
    video_format: VideoFormat
    title: str
    provider: VideoProvider = VideoProvider.KLING
    duration_seconds: float = 0.0
    aspect_ratio: AspectRatio = AspectRatio.VERTICAL
    file_url: str = ""
    storyboard: Storyboard = Field(default_factory=Storyboard)
    prompt_used: str = ""
    platform: str = ""
    brand_alignment_score: float = 0.0
    estimated_completion_rate: float = 0.0
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    variant_ids: list[str] = Field(default_factory=list)

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def to_summary(self) -> str:
        return (
            f"[{self.video_format.value}] '{self.title}' — "
            f"{self.duration_seconds:.0f}s {self.aspect_ratio.value}, "
            f"provider: {self.provider.value}."
        )


class VideoGenerationReport(BaseModel):
    report_id: str = Field(default_factory=lambda: str(uuid4()))
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    assets: list[VideoAsset] = Field(default_factory=list)
    total_generated: int = 0
    total_duration_seconds: float = 0.0
    providers_used: list[str] = Field(default_factory=list)

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
