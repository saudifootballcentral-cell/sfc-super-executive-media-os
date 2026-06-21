"""Influencer Intelligence models — profiles, metrics, and reports."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class InfluencerType(str, Enum):
    JOURNALIST = "journalist"
    CREATOR = "creator"
    ANALYST = "analyst"
    FORMER_PLAYER = "former_player"
    CLUB_ACCOUNT = "club_account"
    MEDIA_ORG = "media_org"


class InfluencerMetrics(BaseModel):
    influence_score: float = 0.0    # 0-100 overall influence
    trust_score: float = 0.0        # 0-100 credibility/accuracy
    reach_score: float = 0.0        # 0-100 audience size relative
    velocity_score: float = 0.0     # 0-100 growth rate
    authority_score: float = 0.0    # 0-100 domain expertise
    engagement_rate: float = 0.0    # % of followers that engage

    model_config = {"frozen": False}

    @property
    def composite_score(self) -> float:
        return round(
            (self.influence_score * 0.3 + self.trust_score * 0.2 +
             self.reach_score * 0.2 + self.authority_score * 0.3),
            1,
        )


class InfluencerProfile(BaseModel):
    influencer_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    handle: str = ""
    influencer_type: InfluencerType = InfluencerType.CREATOR
    platforms: list[str] = Field(default_factory=list)
    followers: int = 0
    metrics: InfluencerMetrics = Field(default_factory=InfluencerMetrics)
    topics: list[str] = Field(default_factory=list)           # football topics covered
    languages: list[str] = Field(default_factory=lambda: ["ar"])
    tracked_since: datetime = Field(default_factory=datetime.utcnow)
    last_active: datetime = Field(default_factory=datetime.utcnow)
    is_verified: bool = False

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def to_summary(self) -> dict[str, Any]:
        return {
            "influencer_id": self.influencer_id,
            "name": self.name,
            "type": self.influencer_type.value,
            "followers": self.followers,
            "composite_score": self.metrics.composite_score,
        }


class InfluencerReport(BaseModel):
    report_id: str = Field(default_factory=lambda: str(uuid4()))
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    top_influencers: list[InfluencerProfile] = Field(default_factory=list)
    influence_rankings: list[dict[str, Any]] = Field(default_factory=list)
    media_map: dict[str, list[str]] = Field(default_factory=dict)   # type → names
    source_rankings: list[dict[str, Any]] = Field(default_factory=list)
    total_tracked: int = 0
    new_influencers: int = 0
    alerts: list[str] = Field(default_factory=list)

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
