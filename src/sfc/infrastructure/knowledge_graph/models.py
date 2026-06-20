"""Models for the Knowledge Graph infrastructure service."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class EntityProfile(BaseModel):
    """Full profile of an entity including all relationships."""

    entity_id: str
    name: str
    entity_type: str
    properties: dict[str, Any] = Field(default_factory=dict)
    relationships: list[dict[str, Any]] = Field(default_factory=list)
    relationship_count: int = 0


class RelationshipMap(BaseModel):
    """Map of relationships for an entity."""

    entity_name: str
    related_entities: list[dict[str, Any]] = Field(default_factory=list)
    relationship_types: list[str] = Field(default_factory=list)
    depth: int = 1


class KGQuery(BaseModel):
    """Query for the knowledge graph."""

    entity_type: str | None = None
    rel_type: str | None = None
    name_pattern: str | None = None
    limit: int = 50


class KGQueryResult(BaseModel):
    """Result of a knowledge graph query."""

    entities: list[dict[str, Any]] = Field(default_factory=list)
    relationships: list[dict[str, Any]] = Field(default_factory=list)
    total_count: int = 0
    query: KGQuery = Field(default_factory=KGQuery)
