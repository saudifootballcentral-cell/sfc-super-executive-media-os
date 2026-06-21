"""Audience Intelligence models — segments, profiles, and reports."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class AudienceSegmentType(str, Enum):
    CORE_FANS = "core_fans"
    CASUAL_VIEWERS = "casual_viewers"
    TRANSFER_WATCHERS = "transfer_watchers"
    STATS_ENTHUSIASTS = "stats_enthusiasts"
    YOUTH_AUDIENCE = "youth_audience"
    INTERNATIONAL_FANS = "international_fans"
    SAUDI_NATIONAL_FANS = "saudi_national_fans"
    FANTASY_PLAYERS = "fantasy_players"


class AudienceSegment(BaseModel):
    segment_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    segment_type: AudienceSegmentType = AudienceSegmentType.CORE_FANS
    size: int = 0
    growth_rate: float = 0.0        # % growth per month
    top_interests: list[str] = Field(default_factory=list)
    preferred_platforms: list[str] = Field(default_factory=list)
    peak_hours: list[int] = Field(default_factory=list)   # UTC hours 0-23
    content_preferences: list[str] = Field(default_factory=list)
    avg_session_minutes: float = 0.0
    retention_rate: float = 0.0     # % retained month over month

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class AudienceProfile(BaseModel):
    profile_id: str = Field(default_factory=lambda: str(uuid4()))
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    total_audience: int = 0
    segments: list[AudienceSegment] = Field(default_factory=list)
    top_platform: str = ""
    peak_day: str = ""              # Monday, Tuesday, etc.
    peak_hour: int = 20             # UTC
    avg_content_consumed_per_day: float = 0.0
    growth_rate_monthly: float = 0.0
    growth_opportunities: list[str] = Field(default_factory=list)
    retention_opportunities: list[str] = Field(default_factory=list)

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class AudienceReport(BaseModel):
    report_id: str = Field(default_factory=lambda: str(uuid4()))
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    profile: AudienceProfile = Field(default_factory=AudienceProfile)
    segment_breakdown: list[dict[str, Any]] = Field(default_factory=list)
    engagement_patterns: dict[str, Any] = Field(default_factory=dict)
    platform_breakdown: dict[str, float] = Field(default_factory=dict)
    recommendations: list[str] = Field(default_factory=list)
    ai_insights: str = ""

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
