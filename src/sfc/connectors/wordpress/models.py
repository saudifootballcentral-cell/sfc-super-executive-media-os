"""WordPress REST API connector models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class WordPressPostStatus(str, Enum):
    PUBLISH = "publish"
    DRAFT = "draft"
    PENDING = "pending"
    PRIVATE = "private"


class WordPressPost(BaseModel):
    post_id: str = Field(default_factory=lambda: str(uuid4()))
    platform_post_id: int = 0
    title: str = ""
    content: str = ""
    excerpt: str = ""
    tags: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    status: WordPressPostStatus = WordPressPostStatus.PUBLISH
    slug: str = ""
    url: str = ""
    featured_media_id: int = 0
    published_at: datetime = Field(default_factory=datetime.utcnow)
    success: bool = True
    error_message: str = ""

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class WordPressMedia(BaseModel):
    media_id: str = Field(default_factory=lambda: str(uuid4()))
    platform_media_id: int = 0
    filename: str = ""
    file_url: str = ""
    alt_text: str = ""
    source_url: str = ""
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    success: bool = True
    error_message: str = ""

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class WordPressConnectorReport(BaseModel):
    report_id: str = Field(default_factory=lambda: str(uuid4()))
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    posts_published: int = 0
    media_uploaded: int = 0
    api_errors: int = 0
    rate_limit_hits: int = 0

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
