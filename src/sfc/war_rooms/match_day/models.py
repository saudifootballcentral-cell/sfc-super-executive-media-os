"""Match Day War Room models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class MatchPhase(str, Enum):
    PRE_MATCH = "pre_match"
    LIVE = "live"
    POST_MATCH = "post_match"
    CLOSED = "closed"


class MatchInfo(BaseModel):
    match_id: str = Field(default_factory=lambda: f"MATCH-{uuid4().hex[:6].upper()}")
    home_team: str
    away_team: str
    competition: str = "Saudi Pro League"
    kickoff_time: datetime | None = None
    venue: str = ""
    metadata: dict[str, Any] = {}


class MatchDayOutput(BaseModel):
    match_id: str
    phase: MatchPhase
    match_brief: dict[str, Any] = {}
    match_report: dict[str, Any] = {}
    tactical_report: dict[str, Any] = {}
    player_ratings: list[dict[str, Any]] = []
    post_match_analysis: dict[str, Any] = {}
    executive_summary: str = ""
    content_plan: list[dict[str, Any]] = []
