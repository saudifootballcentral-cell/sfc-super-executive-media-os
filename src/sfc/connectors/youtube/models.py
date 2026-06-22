"""YouTube API connector models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class VideoPrivacy(str, Enum):
    PUBLIC = "public"
    UNLISTED = "unlisted"
    PRIVATE = "private"


class VideoCategory(str, Enum):
    SPORTS = "17"
    ENTERTAINMENT = "24"
    NEWS = "25"
    PEOPLE = "22"


class UploadStatus(str, Enum):
    PENDING = "pending"
    UPLOADING = "uploading"
    PROCESSING = "processing"
    PUBLISHED = "published"
    FAILED = "failed"


class VideoUploadRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    category: VideoCategory = VideoCategory.SPORTS
    privacy: VideoPrivacy = VideoPrivacy.PUBLIC
    file_url: str = ""
    thumbnail_url: str = ""
    is_short: bool = False
    playlist_id: str = ""
    language: str = "ar"
    made_for_kids: bool = False

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class VideoPublishResult(BaseModel):
    result_id: str = Field(default_factory=lambda: str(uuid4()))
    request_id: str = ""
    video_id: str = ""
    url: str = ""
    status: UploadStatus = UploadStatus.PUBLISHED
    title: str = ""
    is_short: bool = False
    published_at: datetime = Field(default_factory=datetime.utcnow)
    error_message: str = ""
    processing_progress: int = 100

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def to_summary(self) -> str:
        status = self.status.value.upper()
        return f"[YouTube] '{self.title}' [{status}] — id: {self.video_id}, url: {self.url}"


class YouTubeAnalytics(BaseModel):
    video_id: str = ""
    title: str = ""
    views: int = 0
    impressions: int = 0
    ctr: float = 0.0
    watch_time_hours: float = 0.0
    avg_view_duration_seconds: float = 0.0
    avg_view_percentage: float = 0.0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    subscribers_gained: int = 0
    revenue_usd: float = 0.0
    fetched_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class ChannelMetrics(BaseModel):
    channel_id: str = ""
    channel_name: str = "SFC"
    subscriber_count: int = 0
    total_views: int = 0
    video_count: int = 0
    monthly_views: int = 0
    subscriber_growth_30d: int = 0
    avg_views_per_video: float = 0.0
    fetched_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class YouTubeComment(BaseModel):
    comment_id: str = ""
    video_id: str = ""
    text: str = ""
    author: str = ""
    like_count: int = 0
    reply_count: int = 0
    published_at: datetime = Field(default_factory=datetime.utcnow)
    sentiment: str = "neutral"

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class Playlist(BaseModel):
    playlist_id: str = Field(default_factory=lambda: str(uuid4()))
    title: str = ""
    description: str = ""
    video_ids: list[str] = Field(default_factory=list)
    item_count: int = 0
    url: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class YouTubeConnectorReport(BaseModel):
    report_id: str = Field(default_factory=lambda: str(uuid4()))
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    videos_published: int = 0
    shorts_published: int = 0
    total_views: int = 0
    total_impressions: int = 0
    avg_ctr: float = 0.0
    channel_metrics: ChannelMetrics = Field(default_factory=ChannelMetrics)
    recent_publishes: list[VideoPublishResult] = Field(default_factory=list)
    api_errors: int = 0
    rate_limit_hits: int = 0

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
