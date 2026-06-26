"""Video rendering models — templates, specs, jobs, and results."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class RenderStatus(str, Enum):
    PENDING = "pending"
    RENDERING = "rendering"
    COMPLETE = "complete"
    FAILED = "failed"
    DRY_RUN = "dry_run"


class LogoPosition(str, Enum):
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"
    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"


class AudioTrackType(str, Enum):
    ORIGINAL = "original"    # original video audio
    VOICEOVER = "voiceover"  # synthesised voice-over
    MUSIC = "music"          # background music


class RenderMode(str, Enum):
    SINGLE_CLIP = "single_clip"    # brand a single extracted clip
    COMPILATION = "compilation"    # concat multiple clips into a reel


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------

class PlatformRenderSpec(BaseModel):
    """Encoding and dimension spec per target platform."""
    platform: str
    width: int
    height: int
    fps: float = 30.0
    video_bitrate_kbps: int = 4000
    audio_bitrate_kbps: int = 192
    video_codec: str = "libx264"
    audio_codec: str = "aac"
    pixel_format: str = "yuv420p"
    preset: str = "fast"
    max_duration_seconds: float = 3600.0

    model_config = {"frozen": False}


# Platform presets used throughout the service
PLATFORM_SPECS: dict[str, PlatformRenderSpec] = {
    "youtube_video": PlatformRenderSpec(
        platform="youtube_video", width=1920, height=1080, fps=30.0,
        video_bitrate_kbps=6000, audio_bitrate_kbps=192, max_duration_seconds=3600.0,
    ),
    "youtube_short": PlatformRenderSpec(
        platform="youtube_short", width=1080, height=1920, fps=30.0,
        video_bitrate_kbps=3500, audio_bitrate_kbps=128, max_duration_seconds=60.0,
    ),
    "instagram_reel": PlatformRenderSpec(
        platform="instagram_reel", width=1080, height=1920, fps=30.0,
        video_bitrate_kbps=3500, audio_bitrate_kbps=128, max_duration_seconds=90.0,
    ),
    "tiktok": PlatformRenderSpec(
        platform="tiktok", width=1080, height=1920, fps=30.0,
        video_bitrate_kbps=2500, audio_bitrate_kbps=128, max_duration_seconds=180.0,
    ),
    "x_video": PlatformRenderSpec(
        platform="x_video", width=1280, height=720, fps=30.0,
        video_bitrate_kbps=2500, audio_bitrate_kbps=128, max_duration_seconds=140.0,
    ),
}

_DEFAULT_SPEC = PlatformRenderSpec(
    platform="default", width=1920, height=1080, fps=30.0,
    video_bitrate_kbps=4000, audio_bitrate_kbps=192,
)


class SubtitleStyle(BaseModel):
    """FFmpeg drawtext / subtitles filter configuration."""
    font_name: str = "Arial"
    font_size: int = 22
    primary_colour: str = "&H00FFFFFF"   # white (BBG format)
    outline_colour: str = "&H00000000"   # black outline
    outline_width: int = 2
    shadow: int = 1
    # "bottom" = 90% from top, "top" = 10% from top
    vertical_position: str = "bottom"
    burn_in: bool = True  # True = hard-coded into video; False = sidecar .srt only

    model_config = {"frozen": False}


class AudioMixConfig(BaseModel):
    """Volume levels for multi-track audio mixing."""
    original_volume: float = 0.0      # original video audio; 0 = muted (common for voice-over)
    voiceover_volume: float = 1.0
    music_volume: float = 0.12         # background music under voice
    normalize: bool = True             # loudness normalization

    model_config = {"frozen": False}


class RenderTemplate(BaseModel):
    """Brand template applied during rendering."""
    template_id: str = Field(default_factory=lambda: str(uuid4()))
    brand_name: str = "SFC"
    logo_path: str = ""               # absolute path to PNG with transparency
    intro_path: str = ""              # absolute path to intro .mp4 (optional)
    outro_path: str = ""              # absolute path to outro .mp4 (optional)
    logo_position: LogoPosition = LogoPosition.BOTTOM_RIGHT
    logo_scale_px: int = 120          # logo width in pixels
    logo_opacity: float = 0.85
    subtitle_style: SubtitleStyle = Field(default_factory=SubtitleStyle)
    audio_mix: AudioMixConfig = Field(default_factory=AudioMixConfig)
    lower_third_text: str = ""        # e.g. "Saudi Football Central | سعودي فوتبول سنترال"
    primary_color_hex: str = "#00A651"  # SFC green

    model_config = {"frozen": False}


class AudioTrack(BaseModel):
    """One audio track to be mixed into the render."""
    track_id: str = Field(default_factory=lambda: str(uuid4()))
    track_type: AudioTrackType
    local_path: str
    volume: float = 1.0
    start_offset_seconds: float = 0.0  # delay before this track starts

    model_config = {"frozen": False}


# ---------------------------------------------------------------------------
# Result models
# ---------------------------------------------------------------------------

class RenderedVideo(BaseModel):
    """Final output of a render job."""
    render_id: str = Field(default_factory=lambda: str(uuid4()))
    mode: RenderMode
    platform: str
    source_clip_ids: list[str] = Field(default_factory=list)
    local_path: str = ""
    public_url: str = ""              # set after CDN upload
    duration_seconds: float = 0.0
    file_size_bytes: int = 0
    width: int = 0
    height: int = 0
    fps: float = 0.0
    checksum_sha256: str = ""
    status: RenderStatus = RenderStatus.PENDING
    error_message: str = ""
    sidecar_subtitle_paths: dict[str, str] = Field(default_factory=dict)  # lang → .srt path
    ffmpeg_cmd: list[str] = Field(default_factory=list)   # logged for debugging
    dry_run: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"frozen": False}

    @property
    def is_ready(self) -> bool:
        return self.status == RenderStatus.COMPLETE and bool(self.local_path)

    def to_dict(self) -> dict[str, Any]:
        return {
            "render_id": self.render_id,
            "mode": self.mode.value,
            "platform": self.platform,
            "source_clip_ids": self.source_clip_ids,
            "local_path": self.local_path,
            "public_url": self.public_url,
            "duration_seconds": self.duration_seconds,
            "file_size_bytes": self.file_size_bytes,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "status": self.status.value,
            "error_message": self.error_message,
            "sidecar_subtitle_paths": self.sidecar_subtitle_paths,
            "dry_run": self.dry_run,
            "created_at": self.created_at.isoformat(),
        }
