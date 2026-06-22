"""X (Twitter) API connector models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class XPostStatus(str, Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    FAILED = "failed"


class XMediaType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"
    GIF = "gif"


class XPost(BaseModel):
    post_id: str = Field(default_factory=lambda: str(uuid4()))
    text: str = ""
    media_ids: list[str] = Field(default_factory=list)
    platform_post_id: str = ""
    status: XPostStatus = XPostStatus.PUBLISHED
    scheduled_at: datetime | None = None
    published_at: datetime | None = None
    url: str = ""
    reply_to_id: str = ""
    quote_post_id: str = ""
    error_message: str = ""

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def to_summary(self) -> str:
        status = self.status.value.upper()
        return f"[X] [{status}] '{self.text[:60]}...' — id: {self.platform_post_id}"


class XThread(BaseModel):
    thread_id: str = Field(default_factory=lambda: str(uuid4()))
    posts: list[XPost] = Field(default_factory=list)
    topic: str = ""
    total_posts: int = 0
    published_at: datetime | None = None
    status: XPostStatus = XPostStatus.PUBLISHED
    platform_thread_root_id: str = ""

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def to_summary(self) -> str:
        return (
            f"[X Thread] '{self.topic}' — {self.total_posts} posts, "
            f"status: {self.status.value}"
        )


class XMedia(BaseModel):
    media_id: str = Field(default_factory=lambda: str(uuid4()))
    platform_media_id: str = ""
    media_type: XMediaType = XMediaType.IMAGE
    file_url: str = ""
    alt_text: str = ""
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class XMetrics(BaseModel):
    post_id: str = ""
    platform_post_id: str = ""
    views: int = 0
    likes: int = 0
    retweets: int = 0
    quote_tweets: int = 0
    replies: int = 0
    bookmarks: int = 0
    impressions: int = 0
    profile_visits: int = 0
    link_clicks: int = 0
    engagement_rate: float = 0.0
    fetched_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class XTrend(BaseModel):
    term: str = ""
    tweet_volume: int = 0
    trend_type: str = "hashtag"
    location: str = "Saudi Arabia"
    trending_since: datetime = Field(default_factory=datetime.utcnow)
    velocity: float = 0.0
    sentiment: str = "neutral"
    relevance_score: float = 0.0

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class XConversation(BaseModel):
    conversation_id: str = Field(default_factory=lambda: str(uuid4()))
    topic: str = ""
    keyword: str = ""
    posts: list[dict[str, Any]] = Field(default_factory=list)
    participant_count: int = 0
    total_impressions: int = 0
    sentiment: str = "neutral"
    detected_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class XMonitorConfig(BaseModel):
    keywords: list[str] = Field(default_factory=list)
    hashtags: list[str] = Field(default_factory=list)
    accounts: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=lambda: ["ar", "en"])
    geo: str = "SA"

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class XConnectorReport(BaseModel):
    report_id: str = Field(default_factory=lambda: str(uuid4()))
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    posts_published: int = 0
    threads_published: int = 0
    trends_detected: int = 0
    conversations_detected: int = 0
    total_impressions: int = 0
    total_engagements: int = 0
    follower_count: int = 0
    api_errors: int = 0
    rate_limit_hits: int = 0

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
