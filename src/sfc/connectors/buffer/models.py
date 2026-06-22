"""Buffer API connector models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class BufferPlatform(str, Enum):
    INSTAGRAM = "instagram"
    THREADS = "threads"
    FACEBOOK = "facebook"
    TIKTOK = "tiktok"
    LINKEDIN = "linkedin"
    X = "x"
    YOUTUBE = "youtube"


class BufferPostStatus(str, Enum):
    DRAFT = "draft"
    QUEUED = "queued"
    SCHEDULED = "scheduled"
    PUBLISHING = "publishing"
    SENT = "sent"
    PUBLISHED = "published"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class BufferPost(BaseModel):
    post_id: str = Field(default_factory=lambda: str(uuid4()))
    content: str = ""
    media_url: str = ""
    media_type: str = "image"
    platform: BufferPlatform = BufferPlatform.INSTAGRAM
    scheduled_at: datetime | None = None
    published_at: datetime | None = None
    status: BufferPostStatus = BufferPostStatus.SCHEDULED
    platform_post_id: str = ""
    profile_id: str = ""
    hashtags: list[str] = Field(default_factory=list)
    error_message: str = ""
    retry_count: int = 0

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def to_summary(self) -> str:
        return (
            f"[Buffer/{self.platform.value}] '{self.content[:50]}' "
            f"[{self.status.value}]"
        )


class BufferPublishResult(BaseModel):
    result_id: str = Field(default_factory=lambda: str(uuid4()))
    post_id: str = ""
    platform: BufferPlatform = BufferPlatform.INSTAGRAM
    platform_post_id: str = ""
    published_at: datetime = Field(default_factory=datetime.utcnow)
    status: BufferPostStatus = BufferPostStatus.SENT
    error_message: str = ""
    retry_count: int = 0
    url: str = ""

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def to_summary(self) -> str:
        return (
            f"[Buffer/{self.platform.value}] result={self.status.value} "
            f"id={self.platform_post_id}"
        )


class BufferQueue(BaseModel):
    queue_id: str = Field(default_factory=lambda: str(uuid4()))
    posts: list[BufferPost] = Field(default_factory=list)
    pending_count: int = 0
    scheduled_count: int = 0
    sent_count: int = 0
    failed_count: int = 0
    next_publish_at: datetime | None = None
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class BufferMultiPlatformRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    content: str = ""
    media_url: str = ""
    platforms: list[BufferPlatform] = Field(default_factory=list)
    scheduled_at: datetime | None = None
    hashtags: list[str] = Field(default_factory=list)

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class BufferProfile(BaseModel):
    profile_id: str = ""
    service: str = ""
    formatted_service: str = ""
    service_username: str = ""
    formatted_username: str = ""
    platform_key: str = ""
    timezone: str = "UTC"

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class PublishRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    content: str = ""
    media_url: str = ""
    media_type: str = "image"
    platform: BufferPlatform = BufferPlatform.INSTAGRAM
    profile_id: str = ""
    scheduled_at: datetime | None = None
    hashtags: list[str] = Field(default_factory=list)
    governance_approved: bool = False
    operator_approved: bool = False
    rights_status: str = "owned"

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class MediaValidationResult(BaseModel):
    valid: bool = False
    media_url: str = ""
    file_exists: bool = False
    file_size_bytes: int = 0
    checksum_ok: bool = False
    governance_approved: bool = False
    rights_approved: bool = False
    error: str = ""

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class BufferConnectorReport(BaseModel):
    report_id: str = Field(default_factory=lambda: str(uuid4()))
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    posts_created: int = 0
    posts_published: int = 0
    posts_failed: int = 0
    posts_retried: int = 0
    platforms_active: list[str] = Field(default_factory=list)
    success_rate: float = 0.0
    api_errors: int = 0
    rate_limit_hits: int = 0

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
