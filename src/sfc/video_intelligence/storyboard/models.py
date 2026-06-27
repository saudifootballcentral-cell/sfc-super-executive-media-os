"""Storyboard models — bridges script scenes to AI video generation prompts."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4


@dataclass
class StoryboardScene:
    """One scene ready for AI video generation."""
    scene_id: str
    script_scene_id: str
    visual_prompt: str          # English prompt for AI video model
    negative_prompt: str = ""
    duration_seconds: float = 5.0
    aspect_ratio: str = "16:9"  # "16:9" or "9:16"
    reference_image_url: str = ""
    style_tags: list[str] = field(default_factory=list)


@dataclass
class Storyboard:
    """Complete storyboard for one platform output."""
    storyboard_id: str = field(default_factory=lambda: str(uuid4()))
    script_id: str = ""
    platform: str = "youtube_video"
    scenes: list[StoryboardScene] = field(default_factory=list)
    total_duration_seconds: float = 0.0

    @property
    def scene_count(self) -> int:
        return len(self.scenes)
