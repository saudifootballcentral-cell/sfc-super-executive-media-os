"""Footage discovery models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class DiscoverySourceType(str, Enum):
    YOUTUBE_CHANNEL = "youtube_channel"   # YouTube Data API v3 or channel RSS
    RSS_MEDIA_FEED = "rss_media_feed"     # RSS/Atom with <media:content> or <enclosure>
    FOLDER_WATCH = "folder_watch"         # local directory scanner
    DIRECT_URL = "direct_url"             # explicit list of video URLs


class DiscoveryStatus(str, Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"      # submitted to VideoIntelligenceOrchestrator
    SKIPPED_DEDUP = "skipped_dedup"
    SKIPPED_RIGHTS = "skipped_rights"
    DOWNLOAD_FAILED = "download_failed"
    PIPELINE_FAILED = "pipeline_failed"


class DiscoveredAsset(BaseModel):
    """One piece of footage found by a discovery provider."""
    asset_id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    description: str = ""
    url: str = ""              # remote URL (YouTube, direct video link)
    local_path: str = ""       # set after download, or for folder-watch assets
    source_type: str = "youtube_url"   # maps to VideoSourceType.value
    rights_status: str = "unknown"     # maps to RightsStatus.value
    duration_seconds: float = 0.0      # 0 if unknown before download
    thumbnail_url: str = ""
    channel_name: str = ""
    channel_id: str = ""
    published_at: datetime | None = None
    provider_name: str = ""
    status: DiscoveryStatus = DiscoveryStatus.PENDING
    metadata: dict[str, Any] = Field(default_factory=dict)
    discovered_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}

    @property
    def dedup_key(self) -> str:
        """Stable dedup key: prefer URL, fall back to local_path."""
        return (self.url or self.local_path).strip().lower().rstrip("/")

    def to_dict(self) -> dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "title": self.title,
            "url": self.url,
            "local_path": self.local_path,
            "source_type": self.source_type,
            "rights_status": self.rights_status,
            "duration_seconds": self.duration_seconds,
            "channel_name": self.channel_name,
            "provider_name": self.provider_name,
            "status": self.status.value,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "discovered_at": self.discovered_at.isoformat(),
        }


class DiscoveryRun(BaseModel):
    """Summary of one footage discovery scan."""
    run_id: str = Field(default_factory=lambda: str(uuid4()))
    discovered: int = 0
    deduplicated: int = 0
    downloaded: int = 0
    submitted: int = 0
    failed: int = 0
    assets: list[DiscoveredAsset] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None

    model_config = {"frozen": False}

    @property
    def duration_seconds(self) -> float:
        if self.completed_at is None:
            return 0.0
        return (self.completed_at - self.started_at).total_seconds()

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "discovered": self.discovered,
            "deduplicated": self.deduplicated,
            "downloaded": self.downloaded,
            "submitted": self.submitted,
            "failed": self.failed,
            "duration_seconds": self.duration_seconds,
            "errors": self.errors,
            "started_at": self.started_at.isoformat(),
        }
