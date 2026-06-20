"""Knowledge Graph relationship types and records."""

from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class RelationshipType(str, Enum):
    PLAYS_FOR = "plays_for"
    COACHES = "coaches"
    COMPETES_IN = "competes_in"
    SPONSORED_BY = "sponsored_by"
    REPORTED_BY = "reported_by"
    PARTICIPATED_IN = "participated_in"
    CREATED = "created"
    OWNS = "owns"
    MANAGES = "manages"
    RELATED_TO = "related_to"
    GOVERNED_BY = "governed_by"


class Relationship(BaseModel):
    relationship_id: UUID = Field(default_factory=uuid4)
    relationship_type: RelationshipType
    source_entity_id: UUID
    target_entity_id: UUID
    attributes: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=100.0, ge=0.0, le=100.0)

    model_config = {"use_enum_values": True}
