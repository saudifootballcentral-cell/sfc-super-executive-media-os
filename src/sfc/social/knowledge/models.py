"""Social Knowledge Layer models — entities, relations, and knowledge graph."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class EntityType(str, Enum):
    NARRATIVE = "narrative"
    TREND = "trend"
    INFLUENCER = "influencer"
    AUDIENCE_SEGMENT = "audience_segment"
    TOPIC = "topic"
    PLAYER = "player"
    CLUB = "club"
    COMPETITION = "competition"


class RelationType(str, Enum):
    INFLUENCES = "influences"
    SUPPORTS = "supports"
    OPPOSES = "opposes"
    AMPLIFIES = "amplifies"
    DRIVES = "drives"
    CONNECTED_TO = "connected_to"


class KnowledgeEntity(BaseModel):
    entity_id: str = Field(default_factory=lambda: str(uuid4()))
    entity_type: EntityType
    name: str
    properties: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class KnowledgeRelation(BaseModel):
    relation_id: str = Field(default_factory=lambda: str(uuid4()))
    source_id: str
    target_id: str
    relation_type: RelationType
    strength: float = 0.5           # 0.0-1.0
    evidence: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class SocialKnowledgeSnapshot(BaseModel):
    snapshot_id: str = Field(default_factory=lambda: str(uuid4()))
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    total_entities: int = 0
    total_relations: int = 0
    entities_by_type: dict[str, int] = Field(default_factory=dict)
    relations_by_type: dict[str, int] = Field(default_factory=dict)
    top_entities: list[dict[str, Any]] = Field(default_factory=list)
    recent_additions: list[str] = Field(default_factory=list)

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
