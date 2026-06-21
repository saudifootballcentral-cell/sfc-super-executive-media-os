"""Audience Modeling Engine models — digital twins, behavior, and influence."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class AudienceType(str, Enum):
    FAN = "fan"
    SUPPORTER = "supporter"
    CASUAL_FOLLOWER = "casual_follower"
    JOURNALIST = "journalist"
    INFLUENCER = "influencer"
    SPONSOR = "sponsor"
    EXECUTIVE = "executive"


class BehaviorPattern(str, Enum):
    PASSIVE_CONSUMER = "passive_consumer"
    ACTIVE_ENGAGER = "active_engager"
    CONTENT_SHARER = "content_sharer"
    OPINION_LEADER = "opinion_leader"
    TREND_AMPLIFIER = "trend_amplifier"
    BRAND_ADVOCATE = "brand_advocate"


class BehaviorModel(BaseModel):
    primary_pattern: BehaviorPattern = BehaviorPattern.PASSIVE_CONSUMER
    engagement_rate: float = 0.0        # % of content engaged with
    share_propensity: float = 0.0       # 0-100 likelihood to share
    comment_propensity: float = 0.0     # 0-100 likelihood to comment
    narrative_adoption_speed: float = 0.0  # 0-100 how quickly adopts trends
    platform_loyalty: float = 0.0       # 0-100 platform stickiness
    sentiment_volatility: float = 0.0   # 0-100 how quickly sentiment changes
    peak_activity_hours: list[int] = Field(default_factory=list)

    model_config = {"frozen": False}


class ReactionModel(BaseModel):
    positive_content_response: float = 0.0     # 0-100
    negative_content_response: float = 0.0     # 0-100
    controversy_sensitivity: float = 0.0       # 0-100
    transfer_news_response: float = 0.0        # 0-100
    match_result_response: float = 0.0         # 0-100
    player_scandal_response: float = 0.0       # 0-100

    model_config = {"frozen": False}


class AudienceInfluenceModel(BaseModel):
    influenced_by: list[str] = Field(default_factory=list)     # influencer ids
    influenced_platforms: list[str] = Field(default_factory=list)
    influence_susceptibility: float = 0.0       # 0-100 how easily influenced
    peer_influence_weight: float = 0.0          # 0-100 peer vs. media weight
    media_influence_weight: float = 0.0         # 0-100 media vs. peer weight
    official_source_trust: float = 0.0          # 0-100

    model_config = {"frozen": False}


class AudienceDigitalTwin(BaseModel):
    twin_id: str = Field(default_factory=lambda: str(uuid4()))
    audience_type: AudienceType
    name: str = ""
    description: str = ""
    size: int = 0                               # approximate size of segment
    # Models
    behavior_model: BehaviorModel = Field(default_factory=BehaviorModel)
    reaction_model: ReactionModel = Field(default_factory=ReactionModel)
    influence_model: AudienceInfluenceModel = Field(default_factory=AudienceInfluenceModel)
    # Attributes
    preferred_platforms: list[str] = Field(default_factory=list)
    preferred_content_types: list[str] = Field(default_factory=list)
    top_interests: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=lambda: ["ar"])
    # Metrics
    avg_session_minutes: float = 0.0
    monthly_growth_rate: float = 0.0
    retention_rate: float = 0.0
    narrative_adoption_rate: float = 0.0    # 0-100 how quickly adopts new narratives
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def to_summary(self) -> str:
        return (
            f"{self.name} [{self.audience_type.value}] — "
            f"{self.size:,} audience, {self.behavior_model.engagement_rate:.1f}% engagement, "
            f"{self.narrative_adoption_rate:.0f}% narrative adoption."
        )


class AudienceModelReport(BaseModel):
    report_id: str = Field(default_factory=lambda: str(uuid4()))
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    digital_twins: list[AudienceDigitalTwin] = Field(default_factory=list)
    total_modeled_audience: int = 0
    dominant_type: AudienceType = AudienceType.FAN
    key_insights: list[str] = Field(default_factory=list)
    ai_analysis: str = ""

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
