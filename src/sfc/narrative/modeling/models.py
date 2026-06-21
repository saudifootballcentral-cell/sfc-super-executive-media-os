"""Narrative Modeling Engine models — profiles, maps, and influence models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class NarrativeType(str, Enum):
    PLAYER = "player"
    CLUB = "club"
    NATIONAL_TEAM = "national_team"
    TRANSFER = "transfer"
    TOURNAMENT = "tournament"
    SPONSOR = "sponsor"
    MEDIA = "media"
    REFEREE = "referee"
    FAN = "fan"


class NarrativeRelationshipType(str, Enum):
    AMPLIFIES = "amplifies"
    SUPPORTS = "supports"
    OPPOSES = "opposes"
    ORIGINATES = "originates"
    FEEDS = "feeds"
    MERGES = "merges"


class NarrativeRelationship(BaseModel):
    relationship_id: str = Field(default_factory=lambda: str(uuid4()))
    source_narrative_id: str
    target_narrative_id: str
    relationship_type: NarrativeRelationshipType
    strength: float = 0.5               # 0.0 – 1.0
    evidence: str = ""

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class NarrativeInfluenceModel(BaseModel):
    primary_drivers: list[str] = Field(default_factory=list)    # entity names
    amplifiers: list[str] = Field(default_factory=list)
    suppressors: list[str] = Field(default_factory=list)
    platform_weights: dict[str, float] = Field(default_factory=dict)  # platform → weight
    influencer_impact: float = 0.0      # 0-100 weighted influencer contribution
    media_impact: float = 0.0          # 0-100 media coverage contribution
    organic_impact: float = 0.0        # 0-100 grassroots/organic contribution

    model_config = {"frozen": False}


class NarrativeProfile(BaseModel):
    profile_id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    narrative_type: NarrativeType = NarrativeType.PLAYER
    description: str = ""
    entities: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    hashtags: list[str] = Field(default_factory=list)
    # Scores
    strength_score: float = 0.0        # 0-100 overall narrative strength
    momentum_score: float = 0.0        # 0-100 growth momentum
    sentiment_score: float = 0.0       # -100 to 100
    credibility_score: float = 0.0     # 0-100 trustworthiness
    virality_potential: float = 0.0    # 0-100
    # Context
    influence_model: NarrativeInfluenceModel = Field(default_factory=NarrativeInfluenceModel)
    related_narratives: list[str] = Field(default_factory=list)   # profile_ids
    competing_narratives: list[str] = Field(default_factory=list)
    # Metadata
    origin_platform: str = ""
    languages: list[str] = Field(default_factory=lambda: ["ar"])
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def to_summary(self) -> str:
        return (
            f"'{self.title}' [{self.narrative_type.value}] — "
            f"strength: {self.strength_score:.0f}, sentiment: {self.sentiment_score:.0f}, "
            f"virality: {self.virality_potential:.0f}."
        )


class NarrativeMap(BaseModel):
    map_id: str = Field(default_factory=lambda: str(uuid4()))
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    profiles: list[NarrativeProfile] = Field(default_factory=list)
    relationships: list[NarrativeRelationship] = Field(default_factory=list)
    dominant_narrative_id: str = ""
    narrative_clusters: list[list[str]] = Field(default_factory=list)  # clusters of profile_ids
    conflict_pairs: list[tuple[str, str]] = Field(default_factory=list)
    total_active: int = 0

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
