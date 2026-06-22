"""Auto captioning and subtitle models."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field


class CaptionEntry(BaseModel):
    index: int
    start_time: str  # "00:00:01,000"
    end_time: str
    text: str
    language: str = "arabic"

    model_config = {"frozen": False}


class SubtitleTrack(BaseModel):
    track_id: str = Field(default_factory=lambda: str(uuid4()))
    clip_id: str
    language: str = "arabic"
    format: str = "srt"
    entries: list[CaptionEntry] = Field(default_factory=list)
    local_path: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}

    def to_srt(self) -> str:
        lines = []
        for entry in self.entries:
            lines.extend([
                str(entry.index),
                f"{entry.start_time} --> {entry.end_time}",
                entry.text,
                "",
            ])
        return "\n".join(lines)


class CaptioningResult(BaseModel):
    result_id: str = Field(default_factory=lambda: str(uuid4()))
    clip_id: str
    tracks: list[SubtitleTrack] = Field(default_factory=list)
    dry_run: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}

    def track_for(self, language: str) -> SubtitleTrack | None:
        return next((t for t in self.tracks if t.language == language), None)
