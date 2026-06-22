"""Video Ingestion — source and metadata models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class VideoSourceType(str, Enum):
    LOCAL_MP4 = "local_mp4"
    LOCAL_MOV = "local_mov"
    YOUTUBE_URL = "youtube_url"
    UPLOADED_FILE = "uploaded_file"
    PRESS_CONFERENCE = "press_conference"
    INTERVIEW = "interview"
    PODCAST_VIDEO = "podcast_video"
    MATCH_RECORDING = "match_recording"
    TRAINING_VIDEO = "training_video"
    CLUB_MEDIA = "club_media"


class RightsStatus(str, Enum):
    OWNED = "owned"
    LICENSED = "licensed"
    PUBLIC_SOURCE = "public_source"
    UNKNOWN = "unknown"
    RESTRICTED = "restricted"


class VideoProcessingStatus(str, Enum):
    PENDING = "pending"
    INGESTING = "ingesting"
    ANALYZING = "analyzing"
    EXTRACTING = "extracting"
    COMPLETE = "complete"
    FAILED = "failed"
    RIGHTS_BLOCKED = "rights_blocked"
    DUPLICATE = "duplicate"
    DRY_RUN = "dry_run"


class VideoResolution(BaseModel):
    width: int = 1920
    height: int = 1080

    @property
    def label(self) -> str:
        if self.height >= 2160:
            return "4K"
        if self.height >= 1080:
            return "1080p"
        if self.height >= 720:
            return "720p"
        if self.height >= 480:
            return "480p"
        return f"{self.height}p"

    @property
    def aspect_ratio(self) -> str:
        from math import gcd
        d = gcd(self.width, self.height)
        return f"{self.width // d}:{self.height // d}"


class VideoMetadata(BaseModel):
    video_id: str = Field(default_factory=lambda: str(uuid4()))
    title: str = ""
    duration_seconds: float = 0.0
    resolution: VideoResolution = Field(default_factory=VideoResolution)
    fps: float = 30.0
    audio_tracks: int = 1
    file_size_bytes: int = 0
    codec: str = ""
    bitrate_kbps: int = 0
    source_hash: str = ""
    source_type: VideoSourceType = VideoSourceType.LOCAL_MP4
    rights_status: RightsStatus = RightsStatus.UNKNOWN
    language: str = "arabic"
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"frozen": False}

    @property
    def duration_label(self) -> str:
        total = int(self.duration_seconds)
        h, rem = divmod(total, 3600)
        m, s = divmod(rem, 60)
        if h:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"

    @property
    def is_publishable_rights(self) -> bool:
        return self.rights_status in (
            RightsStatus.OWNED,
            RightsStatus.LICENSED,
            RightsStatus.PUBLIC_SOURCE,
        )


class VideoSource(BaseModel):
    source_id: str = Field(default_factory=lambda: str(uuid4()))
    source_type: VideoSourceType
    path: str = ""
    url: str = ""
    title: str = ""
    rights_status: RightsStatus = RightsStatus.UNKNOWN
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
    submitter: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"frozen": False}


class VideoIngestionResult(BaseModel):
    ingestion_id: str = Field(default_factory=lambda: str(uuid4()))
    source: VideoSource
    status: VideoProcessingStatus = VideoProcessingStatus.PENDING
    video_metadata: VideoMetadata | None = None
    error_message: str = ""
    is_duplicate: bool = False
    duplicate_of: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    processing_log: list[str] = Field(default_factory=list)

    model_config = {"frozen": False}

    @property
    def succeeded(self) -> bool:
        return self.status in (
            VideoProcessingStatus.COMPLETE,
            VideoProcessingStatus.DRY_RUN,
            VideoProcessingStatus.ANALYZING,
        )

    def log(self, message: str) -> None:
        self.processing_log.append(f"[{datetime.utcnow().isoformat()}] {message}")


class VideoFrameIndex(BaseModel):
    index_id: str = Field(default_factory=lambda: str(uuid4()))
    video_id: str
    frame_count: int = 0
    sampled_frames: list[dict[str, Any]] = Field(default_factory=list)
    key_frame_timestamps: list[float] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}
