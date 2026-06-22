"""Cross-platform analytics models for Package 9A."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class Platform(str, Enum):
    YOUTUBE = "youtube"
    X = "x"
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    FACEBOOK = "facebook"
    THREADS = "threads"
    SPOTIFY = "spotify"


class MetricType(str, Enum):
    VIEWS = "views"
    IMPRESSIONS = "impressions"
    REACH = "reach"
    CTR = "ctr"
    ENGAGEMENT = "engagement"
    FOLLOWERS = "followers"
    SUBSCRIBERS = "subscribers"
    WATCH_TIME = "watch_time"
    LIKES = "likes"
    SHARES = "shares"
    COMMENTS = "comments"


class AnalyticsSnapshot(BaseModel):
    snapshot_id: str = Field(default_factory=lambda: str(uuid4()))
    platform: Platform
    asset_id: str = ""
    asset_title: str = ""
    metrics: dict[str, float] = Field(default_factory=dict)
    captured_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}

    def get(self, metric: MetricType, default: float = 0.0) -> float:
        return self.metrics.get(metric.value, default)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class PlatformGrowth(BaseModel):
    platform: Platform
    followers_or_subscribers: int = 0
    growth_7d: int = 0
    growth_30d: int = 0
    growth_rate_pct: float = 0.0
    total_views_30d: int = 0
    avg_engagement_rate: float = 0.0
    top_performing_asset_id: str = ""
    captured_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class ConnectorObservability(BaseModel):
    connector: str = ""
    requests_made: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    api_errors: int = 0
    rate_limit_hits: int = 0
    avg_latency_ms: float = 0.0
    total_latency_ms: float = 0.0
    success_rate: float = 0.0
    total_cost_usd: float = 0.0
    last_error: str = ""
    last_request_at: datetime | None = None

    model_config = {"frozen": False}

    def record_success(self, latency_ms: float = 50.0) -> None:
        self.requests_made += 1
        self.successful_requests += 1
        self.total_latency_ms += latency_ms
        self.avg_latency_ms = self.total_latency_ms / max(self.requests_made, 1)
        self.success_rate = (self.successful_requests / max(self.requests_made, 1)) * 100
        self.last_request_at = datetime.utcnow()

    def record_failure(self, error: str = "", rate_limited: bool = False) -> None:
        self.requests_made += 1
        self.failed_requests += 1
        self.api_errors += 1
        if rate_limited:
            self.rate_limit_hits += 1
        if error:
            self.last_error = error
        self.success_rate = (self.successful_requests / max(self.requests_made, 1)) * 100
        self.last_request_at = datetime.utcnow()

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class AnalyticsSyncReport(BaseModel):
    report_id: str = Field(default_factory=lambda: str(uuid4()))
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    snapshots: list[AnalyticsSnapshot] = Field(default_factory=list)
    platform_growth: list[PlatformGrowth] = Field(default_factory=list)
    total_views: int = 0
    total_impressions: int = 0
    total_reach: int = 0
    avg_ctr: float = 0.0
    avg_engagement_rate: float = 0.0
    total_followers: int = 0
    total_subscribers: int = 0
    total_watch_time_hours: float = 0.0
    platforms_synced: list[str] = Field(default_factory=list)
    observability: dict[str, Any] = Field(default_factory=dict)

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def to_summary(self) -> str:
        return (
            f"Analytics sync: {len(self.platforms_synced)} platforms, "
            f"{self.total_views:,} views, {self.total_impressions:,} impressions, "
            f"CTR {self.avg_ctr:.1f}%."
        )
