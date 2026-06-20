"""Core data models for SFC Super Executive Media OS."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class AgentStatus(str, Enum):
    ACTIVE = "active"
    IDLE = "idle"
    DEGRADED = "degraded"
    OFFLINE = "offline"


class ContentStatus(str, Enum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    PUBLISHED = "published"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class EventType(str, Enum):
    TREND_DETECTED = "TrendDetected"
    NEWS_DETECTED = "NewsDetected"
    RUMOR_DETECTED = "RumorDetected"
    MATCH_STARTED = "MatchStarted"
    MATCH_ENDED = "MatchEnded"
    GOAL_SCORED = "GoalScored"
    TRANSFER_RUMOR = "TransferRumor"
    TRANSFER_CONFIRMED = "TransferConfirmed"
    CONTENT_CREATED = "ContentCreated"
    CONTENT_PUBLISHED = "ContentPublished"
    PERFORMANCE_UPDATED = "PerformanceUpdated"
    CRISIS_DETECTED = "CrisisDetected"
    SPONSOR_OPPORTUNITY_DETECTED = "SponsorOpportunityDetected"
    CAMPAIGN_STARTED = "CampaignStarted"
    CAMPAIGN_COMPLETED = "CampaignCompleted"


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


class WarRoom(str, Enum):
    MATCH_DAY = "match_day"
    WORLD_CUP = "world_cup"
    TRANSFER_WINDOW = "transfer_window"
    CRISIS_MANAGEMENT = "crisis_management"


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class SFCBaseModel(BaseModel):
    model_config = {"use_enum_values": True}


# ---------------------------------------------------------------------------
# Scores / Metadata
# ---------------------------------------------------------------------------

class OutputScores(SFCBaseModel):
    confidence_score: float = Field(..., ge=0.0, le=100.0)
    risk_score: float = Field(..., ge=0.0, le=100.0)
    source_count: int = Field(..., ge=0)
    brand_alignment_score: float = Field(..., ge=0.0, le=100.0)

    @property
    def requires_escalation(self) -> bool:
        return self.confidence_score < 85.0


class DecisionEvaluation(SFCBaseModel):
    impact: float = Field(..., ge=0.0, le=10.0)
    confidence: float = Field(..., ge=0.0, le=10.0)
    risk: float = Field(..., ge=0.0, le=10.0)
    cost: float = Field(..., ge=0.0)
    speed: float = Field(..., ge=0.0, le=10.0)
    revenue_potential: float = Field(..., ge=0.0)
    brand_impact: float = Field(..., ge=-10.0, le=10.0)

    @property
    def long_term_value_score(self) -> float:
        return (
            self.impact * 2.0
            + self.confidence * 1.5
            + self.speed
            + self.brand_impact * 1.5
            + (self.revenue_potential / max(self.cost, 1)) * 0.5
            - self.risk * 1.5
        )


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

class SFCEvent(SFCBaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_type: EventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source: str
    status: str = "pending"
    owner: Division | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Agent Registry
# ---------------------------------------------------------------------------

class AgentRecord(SFCBaseModel):
    agent_id: UUID = Field(default_factory=uuid4)
    name: str
    division: Division
    version: str = "1.0.0"
    status: AgentStatus = AgentStatus.IDLE
    owner: str
    capabilities: list[str] = Field(default_factory=list)
    health_score: float = Field(default=100.0, ge=0.0, le=100.0)
    cost_profile: dict[str, float] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Prompt Registry
# ---------------------------------------------------------------------------

class PromptRecord(SFCBaseModel):
    prompt_id: UUID = Field(default_factory=uuid4)
    name: str
    version: str = "1.0.0"
    author: str
    approval_status: str = "pending"
    content: str
    history: list[dict[str, Any]] = Field(default_factory=list)
    rollback_version: str | None = None


# ---------------------------------------------------------------------------
# Capability Registry
# ---------------------------------------------------------------------------

class CapabilityRecord(SFCBaseModel):
    capability_id: UUID = Field(default_factory=uuid4)
    name: str
    description: str
    provider: str
    cost: float = 0.0
    quality: float = Field(default=100.0, ge=0.0, le=100.0)
    fallback_provider: str | None = None


# ---------------------------------------------------------------------------
# Tool Registry
# ---------------------------------------------------------------------------

class ToolRecord(SFCBaseModel):
    tool_id: UUID = Field(default_factory=uuid4)
    name: str
    provider: str
    quota: int | None = None
    permissions: list[str] = Field(default_factory=list)
    cost_profile: dict[str, float] = Field(default_factory=dict)
    status: str = "active"


# ---------------------------------------------------------------------------
# Content
# ---------------------------------------------------------------------------

class Source(SFCBaseModel):
    name: str
    url: str | None = None
    reliability_score: float = Field(default=80.0, ge=0.0, le=100.0)
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)


class ContentItem(SFCBaseModel):
    content_id: UUID = Field(default_factory=uuid4)
    title: str
    body: str
    content_type: str
    platforms: list[Platform] = Field(default_factory=list)
    status: ContentStatus = ContentStatus.DRAFT
    scores: OutputScores | None = None
    sources: list[Source] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    published_at: datetime | None = None
    tags: list[str] = Field(default_factory=list)
    division: Division | None = None

    @property
    def is_publishable(self) -> bool:
        if self.status != ContentStatus.APPROVED:
            return False
        if self.scores and self.scores.requires_escalation:
            return False
        if len(self.sources) < 2:
            return False
        return True


# ---------------------------------------------------------------------------
# Success Metrics
# ---------------------------------------------------------------------------

class SuccessMetrics(SFCBaseModel):
    period_start: datetime
    period_end: datetime
    reach: int = 0
    watch_time_seconds: int = 0
    retention_rate: float = 0.0
    engagement_rate: float = 0.0
    followers_gained: int = 0
    subscribers_gained: int = 0
    revenue: float = 0.0
    authority_score: float = 0.0
    share_of_voice: float = 0.0
    platform: Platform | None = None


# ---------------------------------------------------------------------------
# Episodic Memory
# ---------------------------------------------------------------------------

class Episode(SFCBaseModel):
    episode_id: UUID = Field(default_factory=uuid4)
    event: str
    decision: str
    result: str
    lesson: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    division: Division | None = None
