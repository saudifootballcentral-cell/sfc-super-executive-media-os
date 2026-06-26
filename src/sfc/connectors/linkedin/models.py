"""LinkedIn API connector models."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class LinkedInPost(BaseModel):
    post_id: str = Field(default_factory=lambda: str(uuid4()))
    platform_post_id: str = ""
    text: str = ""
    media_url: str = ""
    media_type: str = ""
    post_urn: str = ""
    url: str = ""
    published_at: datetime = Field(default_factory=datetime.utcnow)
    success: bool = True
    error_message: str = ""

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class LinkedInArticle(BaseModel):
    article_id: str = Field(default_factory=lambda: str(uuid4()))
    platform_article_id: str = ""
    title: str = ""
    content: str = ""
    summary: str = ""
    article_urn: str = ""
    url: str = ""
    published_at: datetime = Field(default_factory=datetime.utcnow)
    success: bool = True
    error_message: str = ""

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class LinkedInAnalytics(BaseModel):
    post_urn: str = ""
    impressions: int = 0
    clicks: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    engagement_rate: float = 0.0
    unique_impressions: int = 0
    fetched_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class LinkedInConnectorReport(BaseModel):
    report_id: str = Field(default_factory=lambda: str(uuid4()))
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    posts_published: int = 0
    articles_published: int = 0
    total_impressions: int = 0
    total_engagement: int = 0
    api_errors: int = 0
    rate_limit_hits: int = 0

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
