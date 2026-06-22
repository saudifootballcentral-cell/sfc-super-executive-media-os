"""Smart Clipping — clip models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


class ClipStatus(str, Enum):
    PENDING = "pending"
    EXTRACTING = "extracting"
    READY = "ready"
    FAILED = "failed"
    REJECTED = "rejected"
    PUBLISHED = "published"
    DRY_RUN = "dry_run"


class ClipSourceType(str, Enum):
    SPORT_EVENT = "sport_event"
    KEY_QUOTE = "key_quote"
    HIGHLIGHT = "highlight"
    MANUAL = "manual"


class VideoClip(BaseModel):
    clip_id: str = Field(default_factory=lambda: str(uuid4()))
    video_id: str
    title: str = ""
    description: str = ""
    start_seconds: float
    end_seconds: float
    duration_seconds: float = 0.0
    clip_type: str = ""
    source_type: ClipSourceType = ClipSourceType.HIGHLIGHT
    local_path: str = ""
    thumbnail_path: str = ""
    file_size_bytes: int = 0
    checksum_sha256: str = ""
    status: ClipStatus = ClipStatus.PENDING
    source_event_id: str | None = None
    source_quote_id: str | None = None
    language: str = "arabic"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"frozen": False}

    @model_validator(mode="after")
    def set_duration(self) -> "VideoClip":
        if self.duration_seconds == 0.0:
            self.duration_seconds = round(self.end_seconds - self.start_seconds, 2)
        return self

    @property
    def is_file_ready(self) -> bool:
        from pathlib import Path
        return (
            self.status in (ClipStatus.READY,)
            and bool(self.local_path)
            and Path(self.local_path).exists()
            and self.file_size_bytes > 0
        )

    @property
    def duration_label(self) -> str:
        total = int(self.duration_seconds)
        m, s = divmod(total, 60)
        return f"{m}:{s:02d}"


class ClipRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    video_id: str
    video_path: str
    title: str
    description: str = ""
    start_seconds: float
    end_seconds: float
    clip_type: str = ""
    source_type: ClipSourceType = ClipSourceType.HIGHLIGHT
    source_event_id: str | None = None
    source_quote_id: str | None = None
    language: str = "arabic"
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"frozen": False}
