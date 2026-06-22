"""Sports event detection models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class SportEventType(str, Enum):
    GOAL = "goal"
    SAVE = "save"
    SKILL = "skill"
    CELEBRATION = "celebration"
    TACTICAL_MOMENT = "tactical_moment"
    CONTROVERSIAL = "controversial"
    NEAR_MISS = "near_miss"
    RED_CARD = "red_card"
    YELLOW_CARD = "yellow_card"
    INJURY = "injury"
    SUBSTITUTION = "substitution"
    PENALTY = "penalty"
    FREE_KICK = "free_kick"
    CORNER = "corner"
    VAR_REVIEW = "var_review"
    CROWD_REACTION = "crowd_reaction"
    COACH_REACTION = "coach_reaction"


class SportEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    video_id: str
    event_type: SportEventType
    start_seconds: float
    end_seconds: float
    confidence: float = 0.0
    description: str = ""
    players_involved: list[str] = Field(default_factory=list)
    team: str = ""
    match_minute: int | None = None
    highlight_score: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"frozen": False}

    @property
    def duration(self) -> float:
        return self.end_seconds - self.start_seconds

    @property
    def clip_start(self) -> float:
        """Suggested clip start with pre-roll context."""
        return max(0.0, self.start_seconds - 5.0)

    @property
    def clip_end(self) -> float:
        """Suggested clip end with post-roll context."""
        return self.end_seconds + 10.0


class EventDetectionResult(BaseModel):
    detection_id: str = Field(default_factory=lambda: str(uuid4()))
    video_id: str
    events: list[SportEvent] = Field(default_factory=list)
    total_events: int = 0
    high_value_events: int = 0
    dry_run: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}

    def top_events(self, n: int = 5) -> list[SportEvent]:
        return sorted(self.events, key=lambda e: e.highlight_score, reverse=True)[:n]

    def events_of_type(self, event_type: SportEventType) -> list[SportEvent]:
        return [e for e in self.events if e.event_type == event_type]
