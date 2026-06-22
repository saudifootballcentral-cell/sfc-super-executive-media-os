"""AI Podcast Factory models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class PodcastType(str, Enum):
    DAILY_SHOW = "daily_show"
    MATCH_RECAP = "match_recap"
    TRANSFER_SHOW = "transfer_show"
    WORLD_CUP_SHOW = "world_cup_show"
    TACTICAL_SHOW = "tactical_show"


class PodcastSegmentType(str, Enum):
    INTRO = "intro"
    CONTENT = "content"
    ANALYSIS = "analysis"
    INTERVIEW = "interview"
    SPONSOR = "sponsor"
    OUTRO = "outro"


class PodcastSegment(BaseModel):
    segment_id: str = Field(default_factory=lambda: str(uuid4()))
    segment_number: int = 1
    segment_type: PodcastSegmentType = PodcastSegmentType.CONTENT
    title: str = ""
    script: str = ""
    duration_minutes: float = 0.0
    speaker: str = "host"
    talking_points: list[str] = Field(default_factory=list)

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class PodcastEpisode(BaseModel):
    episode_id: str = Field(default_factory=lambda: str(uuid4()))
    podcast_type: PodcastType
    episode_title: str
    episode_number: int = 0
    season: int = 1
    segments: list[PodcastSegment] = Field(default_factory=list)
    full_script: str = ""
    total_duration_minutes: float = 0.0
    description: str = ""
    show_notes: str = ""
    chapters: list[dict[str, Any]] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    publishing_metadata: dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def to_summary(self) -> str:
        return (
            f"[{self.podcast_type.value}] '{self.episode_title}' "
            f"(EP{self.episode_number}) — "
            f"{len(self.segments)} segments, {self.total_duration_minutes:.0f} min."
        )
