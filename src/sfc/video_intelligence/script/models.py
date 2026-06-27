"""Script generation models for AI video production (Mode B)."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4


@dataclass
class ScriptScene:
    """One scene in a generated video script."""
    scene_id: str
    title: str
    description: str        # visual description — what to show
    narration: str          # Arabic voice-over text for this scene
    duration_seconds: float
    visual_style: str       # "energetic", "calm", "dramatic", "celebratory"
    keywords: list[str] = field(default_factory=list)  # for AI video prompt generation


@dataclass
class VideoScript:
    """Complete AI-generated script for a video."""
    script_id: str = field(default_factory=lambda: str(uuid4()))
    topic: str = ""
    total_duration_seconds: float = 0.0
    scenes: list[ScriptScene] = field(default_factory=list)
    language: str = "ar"
    style: str = "sports_highlight"
    generated_by: str = "claude"

    @property
    def scene_count(self) -> int:
        return len(self.scenes)

    @property
    def total_narration(self) -> str:
        return " ".join(s.narration for s in self.scenes)
