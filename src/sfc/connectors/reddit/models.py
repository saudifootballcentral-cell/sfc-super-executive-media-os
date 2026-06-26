"""Reddit API connector models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class RedditPostType(str, Enum):
    TEXT = "text"
    LINK = "link"
    IMAGE = "image"
    VIDEO = "video"


class RedditPost(BaseModel):
    post_id: str = Field(default_factory=lambda: str(uuid4()))
    platform_post_id: str = ""
    subreddit: str = ""
    title: str = ""
    text: str = ""
    url: str = ""
    post_type: RedditPostType = RedditPostType.TEXT
    permalink: str = ""
    published_at: datetime = Field(default_factory=datetime.utcnow)
    success: bool = True
    error_message: str = ""

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class RedditAnalytics(BaseModel):
    post_id: str = ""
    upvotes: int = 0
    downvotes: int = 0
    score: int = 0
    upvote_ratio: float = 0.0
    num_comments: int = 0
    awards: int = 0
    views: int = 0
    fetched_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class RedditConnectorReport(BaseModel):
    report_id: str = Field(default_factory=lambda: str(uuid4()))
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    posts_created: int = 0
    total_upvotes: int = 0
    total_comments: int = 0
    api_errors: int = 0
    rate_limit_hits: int = 0

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
