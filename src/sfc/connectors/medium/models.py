"""Medium API connector models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class MediumPublishStatus(str, Enum):
    PUBLIC = "public"
    DRAFT = "draft"
    UNLISTED = "unlisted"


class MediumPost(BaseModel):
    post_id: str = Field(default_factory=lambda: str(uuid4()))
    platform_post_id: str = ""
    title: str = ""
    content_html: str = ""
    tags: list[str] = Field(default_factory=list)
    publish_status: MediumPublishStatus = MediumPublishStatus.PUBLIC
    publication_id: str = ""
    url: str = ""
    canonical_url: str = ""
    published_at: datetime = Field(default_factory=datetime.utcnow)
    success: bool = True
    error_message: str = ""

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class MediumConnectorReport(BaseModel):
    report_id: str = Field(default_factory=lambda: str(uuid4()))
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    posts_published: int = 0
    publication_posts: int = 0
    api_errors: int = 0
    rate_limit_hits: int = 0

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
