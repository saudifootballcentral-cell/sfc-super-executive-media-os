"""Instagram Direct Graph API connector models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class InstagramMediaType(str, Enum):
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
    CAROUSEL = "CAROUSEL_ALBUM"
    REEL = "REELS"
    STORY = "STORY"


class InstagramPost(BaseModel):
    post_id: str = Field(default_factory=lambda: str(uuid4()))
    platform_media_id: str = ""
    caption: str = ""
    image_url: str = ""
    media_type: InstagramMediaType = InstagramMediaType.IMAGE
    permalink: str = ""
    published_at: datetime = Field(default_factory=datetime.utcnow)
    success: bool = True
    error_message: str = ""

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class InstagramReel(BaseModel):
    reel_id: str = Field(default_factory=lambda: str(uuid4()))
    platform_media_id: str = ""
    caption: str = ""
    video_url: str = ""
    permalink: str = ""
    published_at: datetime = Field(default_factory=datetime.utcnow)
    success: bool = True
    error_message: str = ""

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class InstagramStory(BaseModel):
    story_id: str = Field(default_factory=lambda: str(uuid4()))
    platform_media_id: str = ""
    media_url: str = ""
    media_type: str = "image"
    published_at: datetime = Field(default_factory=datetime.utcnow)
    success: bool = True
    error_message: str = ""

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class InstagramInsights(BaseModel):
    media_id: str = ""
    impressions: int = 0
    reach: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    engagement_rate: float = 0.0
    fetched_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class InstagramConnectorReport(BaseModel):
    report_id: str = Field(default_factory=lambda: str(uuid4()))
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    posts_published: int = 0
    reels_published: int = 0
    stories_published: int = 0
    total_impressions: int = 0
    total_reach: int = 0
    api_errors: int = 0
    rate_limit_hits: int = 0

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
