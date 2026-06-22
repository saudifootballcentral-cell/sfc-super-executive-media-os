"""Video Understanding — transcript, scene, and frame index models."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class TranscriptSegment(BaseModel):
    segment_id: str = Field(default_factory=lambda: str(uuid4()))
    start_seconds: float
    end_seconds: float
    text: str
    speaker: str = ""
    language: str = "arabic"
    confidence: float = 1.0

    model_config = {"frozen": False}

    @property
    def duration(self) -> float:
        return self.end_seconds - self.start_seconds


class VideoTranscript(BaseModel):
    transcript_id: str = Field(default_factory=lambda: str(uuid4()))
    video_id: str
    segments: list[TranscriptSegment] = Field(default_factory=list)
    full_text: str = ""
    language: str = "arabic"
    provider: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}

    @property
    def duration_covered(self) -> float:
        if not self.segments:
            return 0.0
        return max(s.end_seconds for s in self.segments)

    def segments_in_range(
        self, start: float, end: float
    ) -> list[TranscriptSegment]:
        return [
            s for s in self.segments
            if s.start_seconds < end and s.end_seconds > start
        ]

    def text_in_range(self, start: float, end: float) -> str:
        return " ".join(s.text for s in self.segments_in_range(start, end))


class SceneSegment(BaseModel):
    scene_id: str = Field(default_factory=lambda: str(uuid4()))
    start_seconds: float
    end_seconds: float
    scene_type: str = ""
    confidence: float = 1.0
    description: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"frozen": False}

    @property
    def duration(self) -> float:
        return self.end_seconds - self.start_seconds


class VideoUnderstandingResult(BaseModel):
    understanding_id: str = Field(default_factory=lambda: str(uuid4()))
    video_id: str
    transcript: VideoTranscript | None = None
    scenes: list[SceneSegment] = Field(default_factory=list)
    frame_index: "VideoFrameIndex | None" = None
    summary: str = ""
    language_detected: str = "arabic"
    provider: str = ""
    dry_run: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}

    @property
    def has_transcript(self) -> bool:
        return self.transcript is not None and bool(self.transcript.segments)

    @property
    def total_scenes(self) -> int:
        return len(self.scenes)


# Avoid circular import — defined here since referenced in VideoUnderstandingResult
from sfc.video_intelligence.ingestion.models import VideoFrameIndex  # noqa: E402

VideoUnderstandingResult.model_rebuild()
