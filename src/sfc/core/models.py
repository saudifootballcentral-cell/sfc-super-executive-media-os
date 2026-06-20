"""Core domain models for SFC Super Executive Media OS."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class TaskType(str, Enum):
    NEWS = "news"
    MATCH = "match"
    TRANSFER = "transfer"
    TREND = "trend"
    CRISIS = "crisis"
    ANALYSIS = "analysis"
    CAMPAIGN = "campaign"


class ContentStatus(str, Enum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class Platform(str, Enum):
    TIKTOK = "tiktok"
    INSTAGRAM_REELS = "instagram_reels"
    INSTAGRAM_STORIES = "instagram_stories"
    INSTAGRAM_FEED = "instagram_feed"
    YOUTUBE_SHORTS = "youtube_shorts"
    YOUTUBE = "youtube"
    X = "x"
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    WEBSITE = "website"
    NEWSLETTER = "newsletter"


class Division(str, Enum):
    STRATEGIC_PLANNING = "strategic_planning"
    INTELLIGENCE = "intelligence"
    EDITORIAL = "editorial"
    CREATIVE = "creative"
    PUBLISHING = "publishing"
    ANALYTICS = "analytics"
    REVENUE = "revenue"
    GOVERNANCE = "governance"
    AGENTOPS = "agentops"


class Priority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RiskLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ---------------------------------------------------------------------------
# Output Scores — enforced by Governance
# ---------------------------------------------------------------------------

class OutputScores(BaseModel):
    confidence_score: float = Field(..., ge=0.0, le=100.0)
    risk_score: float = Field(..., ge=0.0, le=100.0)
    source_count: int = Field(..., ge=0)
    brand_alignment_score: float = Field(..., ge=0.0, le=100.0)

    model_config = {"frozen": True}

    @property
    def requires_escalation(self) -> bool:
        return self.confidence_score < 85.0

    @property
    def is_publishable(self) -> bool:
        return (
            self.confidence_score >= 85.0
            and self.source_count >= 2
            and self.brand_alignment_score >= 70.0
        )


# ---------------------------------------------------------------------------
# Source — verified information origin
# ---------------------------------------------------------------------------

class Source(BaseModel):
    name: str
    url: str | None = None
    reliability_score: float = Field(default=80.0, ge=0.0, le=100.0)
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"use_enum_values": True}


# ---------------------------------------------------------------------------
# Content Item — the atomic unit of content
# ---------------------------------------------------------------------------

class ContentItem(BaseModel):
    content_id: UUID = Field(default_factory=uuid4)
    title: str
    body: str
    content_type: str
    platforms: list[Platform] = Field(default_factory=list)
    status: ContentStatus = ContentStatus.DRAFT
    scores: OutputScores | None = None
    sources: list[Source] = Field(default_factory=list)
    division: Division | None = None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    published_at: datetime | None = None

    model_config = {"use_enum_values": True}

    @property
    def passes_governance(self) -> bool:
        if self.status not in (ContentStatus.APPROVED,):
            return False
        if len(self.sources) < 2:
            return False
        if self.scores is None:
            return False
        return self.scores.is_publishable


# ---------------------------------------------------------------------------
# Executive Decision — Claude's routing and priority assessment
# ---------------------------------------------------------------------------

class ExecutiveDecision(BaseModel):
    task_analysis: str
    priority: Priority
    risk_level: RiskLevel
    recommended_divisions: list[Division]
    content_strategy: str
    routing: str = "planning"
    rationale: str
    estimated_reach: int = 0
    revenue_opportunity: bool = False

    model_config = {"use_enum_values": True}


# ---------------------------------------------------------------------------
# Execution Plan — from Planning Node
# ---------------------------------------------------------------------------

class ExecutionPlan(BaseModel):
    plan_id: UUID = Field(default_factory=uuid4)
    task_type: TaskType
    priority: Priority
    divisions_required: list[Division]
    platforms_targeted: list[Platform]
    content_types: list[str]
    kpi_targets: dict[str, Any] = Field(default_factory=dict)
    parallel_tasks: list[str] = Field(default_factory=list)
    sequential_tasks: list[str] = Field(default_factory=list)
    estimated_duration_minutes: int = 30
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"use_enum_values": True}


# ---------------------------------------------------------------------------
# Episode — Episodic memory record
# ---------------------------------------------------------------------------

class Episode(BaseModel):
    episode_id: UUID = Field(default_factory=uuid4)
    run_id: str
    event: str
    decision: str
    result: str
    lesson: str
    division: Division | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"use_enum_values": True}
