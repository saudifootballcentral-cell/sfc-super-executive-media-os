"""Unified analytics record — normalises data from all platform providers."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class AnalyticsPlatform(str, Enum):
    YOUTUBE = "youtube"
    X = "x"
    BUFFER = "buffer"
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    FACEBOOK = "facebook"
    AGGREGATE = "aggregate"


class ContentType(str, Enum):
    VIDEO = "video"
    SHORT = "short"
    POST = "post"
    THREAD = "thread"
    STORY = "story"
    REEL = "reel"
    PODCAST = "podcast"
    IMAGE = "image"
    UNKNOWN = "unknown"


class UnifiedAnalyticsRecord(BaseModel):
    """Platform-normalised analytics snapshot for a single published piece of content."""

    record_id: str = Field(default_factory=lambda: str(uuid4()))
    content_id: str = ""
    platform: AnalyticsPlatform = AnalyticsPlatform.AGGREGATE
    content_type: ContentType = ContentType.UNKNOWN

    # Core engagement metrics
    views: int = 0
    impressions: int = 0
    reach: int = 0
    likes: int = 0
    shares: int = 0
    comments: int = 0
    saves: int = 0
    clicks: int = 0
    bookmarks: int = 0
    reposts: int = 0
    replies: int = 0

    # Video-specific
    watch_time_seconds: float = 0.0
    avg_view_duration_seconds: float = 0.0
    retention_rate: float = 0.0  # 0.0–100.0

    # Growth
    subscribers_gained: int = 0
    followers_gained: int = 0
    profile_visits: int = 0

    # Rate metrics (computed)
    engagement_rate: float = 0.0   # (likes+shares+comments)/views × 100
    ctr: float = 0.0               # clicks/impressions × 100
    completion_rate: float = 0.0   # views_to_end / views × 100

    # Revenue (optional)
    estimated_revenue_usd: float = 0.0
    cpm_usd: float = 0.0

    # Metadata
    period_start: datetime = Field(default_factory=datetime.utcnow)
    period_end: datetime = Field(default_factory=datetime.utcnow)
    fetched_at: datetime = Field(default_factory=datetime.utcnow)
    run_id: str = ""
    persona_id: str = ""
    campaign_id: str = ""
    war_room_id: str = ""
    topic: str = ""
    tags: list[str] = Field(default_factory=list)

    # Raw platform data (for audit)
    raw: dict[str, Any] = Field(default_factory=dict)

    model_config = {"frozen": False}

    def compute_rates(self) -> None:
        """Re-compute derived rate metrics from raw counts."""
        base = max(self.views, 1)
        self.engagement_rate = round((self.likes + self.shares + self.comments) / base * 100, 4)
        if self.impressions > 0:
            self.ctr = round(self.clicks / self.impressions * 100, 4)
        if self.views > 0 and self.watch_time_seconds > 0 and self.avg_view_duration_seconds > 0:
            self.completion_rate = round(self.avg_view_duration_seconds / max(self.watch_time_seconds / max(self.views, 1), 1) * 100, 2)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class AggregatedPerformance(BaseModel):
    """Rolled-up analytics across multiple records."""

    agg_id: str = Field(default_factory=lambda: str(uuid4()))
    dimension: str = ""           # "platform", "persona", "campaign", "topic", etc.
    dimension_value: str = ""
    period: str = ""              # "hourly", "daily", "weekly", "monthly"
    record_count: int = 0

    total_views: int = 0
    total_impressions: int = 0
    total_reach: int = 0
    total_likes: int = 0
    total_shares: int = 0
    total_comments: int = 0
    total_watch_time_seconds: float = 0.0

    avg_engagement_rate: float = 0.0
    avg_retention_rate: float = 0.0
    avg_ctr: float = 0.0
    top_content_id: str = ""
    top_content_views: int = 0

    subscribers_gained: int = 0
    followers_gained: int = 0

    generated_at: datetime = Field(default_factory=datetime.utcnow)
    records: list[str] = Field(default_factory=list)  # record_ids

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
