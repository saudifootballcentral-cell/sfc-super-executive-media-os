"""Facebook Graph API connector models."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class FacebookPost(BaseModel):
    post_id: str = Field(default_factory=lambda: str(uuid4()))
    platform_post_id: str = ""
    message: str = ""
    link: str = ""
    photo_url: str = ""
    video_url: str = ""
    post_type: str = "text"
    permalink: str = ""
    published_at: datetime = Field(default_factory=datetime.utcnow)
    success: bool = True
    error_message: str = ""

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class FacebookInsights(BaseModel):
    post_id: str = ""
    impressions: int = 0
    reach: int = 0
    engaged_users: int = 0
    reactions: int = 0
    comments: int = 0
    shares: int = 0
    link_clicks: int = 0
    engagement_rate: float = 0.0
    fetched_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class FacebookConnectorReport(BaseModel):
    report_id: str = Field(default_factory=lambda: str(uuid4()))
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    posts_published: int = 0
    photo_posts_published: int = 0
    video_posts_published: int = 0
    total_reach: int = 0
    total_impressions: int = 0
    api_errors: int = 0
    rate_limit_hits: int = 0

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
