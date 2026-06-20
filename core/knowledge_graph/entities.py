"""Knowledge Graph entities."""

from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class EntityType(str, Enum):
    PLAYER = "player"
    CLUB = "club"
    COMPETITION = "competition"
    COACH = "coach"
    MATCH = "match"
    SPONSOR = "sponsor"
    JOURNALIST = "journalist"
    CONTENT = "content"
    CAMPAIGN = "campaign"
    TOURNAMENT = "tournament"
    BRAND = "brand"


class Entity(BaseModel):
    entity_id: UUID = Field(default_factory=uuid4)
    entity_type: EntityType
    name: str
    attributes: dict[str, Any] = Field(default_factory=dict)
    aliases: list[str] = Field(default_factory=list)

    model_config = {"use_enum_values": True}
