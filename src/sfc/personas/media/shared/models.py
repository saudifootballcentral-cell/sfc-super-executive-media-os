from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4
from pydantic import BaseModel, Field


class Platform(str, Enum):
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"
    YOUTUBE = "youtube"
    X = "x"
    SHORTS = "shorts"
    DOCUMENTARY = "documentary"
    THUMBNAIL = "thumbnail"
    POSTER = "poster"
    GRAPHICS = "graphics"
    PODCAST = "podcast"
    SEO = "seo"
    NEWSLETTER = "newsletter"
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"


class ContentFormat(str, Enum):
    SHORT_VIDEO = "short_video"
    LONG_VIDEO = "long_video"
    REEL = "reel"
    STORY = "story"
    CAROUSEL = "carousel"
    THREAD = "thread"
    ARTICLE = "article"
    GRAPHIC = "graphic"
    PODCAST_EPISODE = "podcast_episode"
    NEWSLETTER = "newsletter"
    ALERT = "alert"


class ViralityScore(str, Enum):
    VIRAL = "viral"        # >= 85
    HIGH = "high"          # 70-84
    MEDIUM = "medium"      # 50-69
    LOW = "low"            # < 50


class PlatformInsight(BaseModel):
    insight_id: str = Field(default_factory=lambda: f"MEDIA-{uuid4().hex[:8].upper()}")
    persona_id: str
    persona_name: str
    platform: Platform
    content_format: ContentFormat
    title: str
    summary: str
    hook: str = ""
    key_recommendations: list[str] = Field(default_factory=list)
    optimization_tips: list[str] = Field(default_factory=list)
    predicted_reach: int = 0
    predicted_engagement_rate: float = 0.0  # 0-100
    predicted_ctr: float = 0.0              # 0-100
    virality_score: float = 0.0             # 0-100
    virality_level: ViralityScore = ViralityScore.MEDIUM
    best_posting_time: str = "18:00-21:00"
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class ContentRecommendation(BaseModel):
    rec_id: str = Field(default_factory=lambda: f"REC-{uuid4().hex[:6].upper()}")
    platform: Platform
    content_type: str
    title: str
    description: str
    target_audience: str = "Saudi football fans"
    estimated_reach: int = 0
    priority: str = "medium"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AudienceSignal(BaseModel):
    signal_id: str = Field(default_factory=lambda: f"SIG-{uuid4().hex[:6].upper()}")
    platform: Platform
    signal_type: str                        # "trending", "declining", "stable"
    metric_name: str
    metric_value: float
    benchmark: float
    vs_benchmark: float                     # % diff from benchmark
    detected_at: datetime = Field(default_factory=datetime.utcnow)


class PerformanceMetrics(BaseModel):
    persona_id: str
    platform: Platform
    views: int = 0
    reach: int = 0
    ctr: float = 0.0
    retention_rate: float = 0.0
    watch_time_seconds: float = 0.0
    engagement_rate: float = 0.0
    shares: int = 0
    saves: int = 0
    followers_gained: int = 0
    conversions: int = 0
    measured_at: datetime = Field(default_factory=datetime.utcnow)


class CreativeDirection(BaseModel):
    direction_id: str = Field(default_factory=lambda: f"CD-{uuid4().hex[:6].upper()}")
    platform: Platform
    visual_style: str
    color_palette: list[str] = Field(default_factory=list)
    typography: str = ""
    mood: str = ""
    reference_formats: list[str] = Field(default_factory=list)
    do_list: list[str] = Field(default_factory=list)
    dont_list: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
