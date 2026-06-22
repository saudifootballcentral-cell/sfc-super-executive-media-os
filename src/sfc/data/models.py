"""Core data models for Package 10A — Real Data Layer."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DataPoint(BaseModel):
    """A single normalised data observation from any provider."""

    model_config = {"frozen": False}

    # Identity
    data_source: str = "mock_fixture"
    source_url: str = ""
    collected_at: datetime = Field(default_factory=datetime.utcnow)
    content_hash: str = ""

    # Quality scores (0-100)
    confidence_score: float = 0.0
    freshness_score: float = 100.0

    # Trend / social metrics
    term: str = ""
    tweet_volume: int = 0
    velocity: float = 0.0
    sentiment_label: str = "neutral"
    relevance_score: float = 0.0
    category: str = ""

    # Sentiment metrics
    sentiment_score: float = 0.0
    momentum: float = 0.0
    volatility: float = 0.0
    sample_size: int = 0

    # Engagement metrics
    views: int = 0
    likes: int = 0
    shares: int = 0
    comments_count: int = 0
    impressions: int = 0
    engagement_rate: float = 0.0

    # YouTube-specific
    watch_time_hours: float = 0.0
    avg_view_duration_seconds: float = 0.0
    avg_view_percentage: float = 0.0
    subscribers_gained: int = 0
    ctr: float = 0.0

    # Influencer metrics
    influence_score: float = 0.0
    trust_score: float = 0.0
    velocity_score: float = 0.0
    authority_score: float = 0.0
    follower_count: int = 0

    # Audience segment metrics
    segment_size: int = 0
    growth_rate: float = 0.0
    avg_session_minutes: float = 0.0
    retention_rate: float = 0.0
    avg_content_per_day: float = 0.0

    # Narrative metrics
    strength_score: float = 0.0
    virality_potential: float = 0.0
    credibility_score: float = 0.0

    # Virality forecast
    expected_reach: int = 0
    expected_engagement: int = 0
    expected_shares: int = 0
    expected_views: int = 0
    expected_watch_time_seconds: float = 0.0
    expected_follower_growth: int = 0

    # News / RSS
    headline: str = ""
    summary: str = ""
    author: str = ""
    language: str = "en"
    tags: list[str] = Field(default_factory=list)

    # Extra raw payload
    raw: dict[str, Any] = Field(default_factory=dict)

    def compute_hash(self) -> "DataPoint":
        """Compute content_hash from term + headline + source_url."""
        content = f"{self.term}|{self.headline}|{self.source_url}"
        self.content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        return self

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class DataBatch(BaseModel):
    """Collection of DataPoints returned from a single provider fetch."""

    model_config = {"frozen": False}

    provider: str = ""
    data_source: str = "mock_fixture"
    fetched_at: datetime = Field(default_factory=datetime.utcnow)
    points: list[DataPoint] = Field(default_factory=list)
    total_fetched: int = 0
    total_deduplicated: int = 0
    errors: list[str] = Field(default_factory=list)

    def __len__(self) -> int:
        return len(self.points)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class IngestionResult(BaseModel):
    """Summary result from a full data ingestion run."""

    model_config = {"frozen": False}

    run_id: str = ""
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime = Field(default_factory=datetime.utcnow)
    providers_used: list[str] = Field(default_factory=list)
    total_points: int = 0
    deduplicated_points: int = 0
    avg_confidence_score: float = 0.0
    avg_freshness_score: float = 0.0
    errors: list[str] = Field(default_factory=list)
    data_sources: list[str] = Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
