"""Press conference and interview detection models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class InterviewSegmentType(str, Enum):
    PLAYER_INTERVIEW = "player_interview"
    COACH_INTERVIEW = "coach_interview"
    PRESS_CONFERENCE = "press_conference"
    PUNDIT_ANALYSIS = "pundit_analysis"
    FAN_INTERVIEW = "fan_interview"
    UNKNOWN = "unknown"


class SpeakerSegment(BaseModel):
    segment_id: str = Field(default_factory=lambda: str(uuid4()))
    start_seconds: float
    end_seconds: float
    speaker_id: str = ""
    speaker_name: str = ""
    speaker_role: str = ""
    text: str = ""
    language: str = "arabic"
    confidence: float = 1.0

    model_config = {"frozen": False}

    @property
    def duration(self) -> float:
        return self.end_seconds - self.start_seconds


class KeyQuote(BaseModel):
    quote_id: str = Field(default_factory=lambda: str(uuid4()))
    video_id: str
    start_seconds: float
    end_seconds: float
    text: str
    speaker_name: str = ""
    speaker_role: str = ""
    language: str = "arabic"
    importance_score: float = 0.0
    topics: list[str] = Field(default_factory=list)
    sentiment: str = "neutral"
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"frozen": False}

    @property
    def duration(self) -> float:
        return self.end_seconds - self.start_seconds

    @property
    def clip_start(self) -> float:
        return max(0.0, self.start_seconds - 2.0)

    @property
    def clip_end(self) -> float:
        return self.end_seconds + 3.0


class InterviewDetectionResult(BaseModel):
    detection_id: str = Field(default_factory=lambda: str(uuid4()))
    video_id: str
    segment_type: InterviewSegmentType = InterviewSegmentType.UNKNOWN
    speaker_segments: list[SpeakerSegment] = Field(default_factory=list)
    key_quotes: list[KeyQuote] = Field(default_factory=list)
    total_duration_seconds: float = 0.0
    speakers_identified: int = 0
    dry_run: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}

    def top_quotes(self, n: int = 3) -> list[KeyQuote]:
        return sorted(
            self.key_quotes, key=lambda q: q.importance_score, reverse=True
        )[:n]

    @property
    def total_quotes(self) -> int:
        return len(self.key_quotes)
