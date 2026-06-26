"""TikTok Direct API connector models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class TikTokVideoStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    PUBLISHED = "published"
    FAILED = "failed"


class TikTokVideo(BaseModel):
    video_id: str = Field(default_factory=lambda: str(uuid4()))
    platform_video_id: str = ""
    title: str = ""
    description: str = ""
    video_url: str = ""
    hashtags: list[str] = Field(default_factory=list)
    status: TikTokVideoStatus = TikTokVideoStatus.PUBLISHED
    share_url: str = ""
    published_at: datetime = Field(default_factory=datetime.utcnow)
    success: bool = True
    error_message: str = ""

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class TikTokAnalytics(BaseModel):
    video_id: str = ""
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    reach: int = 0
    engagement_rate: float = 0.0
    avg_watch_time_seconds: float = 0.0
    completion_rate: float = 0.0
    fetched_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class TikTokTrend(BaseModel):
    hashtag: str = ""
    view_count: int = 0
    video_count: int = 0
    trend_score: float = 0.0
    location: str = "SA"
    fetched_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class TikTokConnectorReport(BaseModel):
    report_id: str = Field(default_factory=lambda: str(uuid4()))
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    videos_published: int = 0
    total_views: int = 0
    total_likes: int = 0
    api_errors: int = 0
    rate_limit_hits: int = 0

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
