"""Knowledge Graph — directed property graph for Saudi football domain knowledge.

Example:
    Salem AlDossari → plays_for → Al Hilal
    Al Hilal → competes_in → Saudi Pro League
    Saudi Pro League → governed_by → SAFF
"""

from __future__ import annotations

import logging
import threading
from collections import defaultdict
from typing import Any
from uuid import UUID

from sfc.knowledge_graph.entities import Entity, EntityType
from sfc.knowledge_graph.relationships import Relationship, RelationshipType

logger = logging.getLogger("sfc.knowledge_graph")


class KnowledgeGraph:
    """Thread-safe directed property graph for Saudi football domain knowledge."""

    def __init__(self) -> None:
        self._entities: dict[UUID, Entity] = {}
        self._relationships: dict[UUID, Relationship] = {}
        self._name_index: dict[str, UUID] = {}
        self._type_index: dict[str, list[UUID]] = defaultdict(list)
        self._adjacency: dict[UUID, list[UUID]] = defaultdict(list)
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Entities
    # ------------------------------------------------------------------

    def add_entity(self, entity: Entity) -> Entity:
        with self._lock:
            self._entities[entity.entity_id] = entity
            self._name_index[entity.name.lower()] = entity.entity_id
            for alias in entity.aliases:
                self._name_index[alias.lower()] = entity.entity_id
            self._type_index[entity.entity_type].append(entity.entity_id)
        logger.debug("[KG] Added entity: %s (%s)", entity.name, entity.entity_type)
        return entity

    def upsert_entity(self, entity_type: EntityType, name: str, attributes: dict[str, Any] | None = None) -> Entity:
        existing = self.find_by_name(name)
        if existing:
            return existing
        entity = Entity(entity_type=entity_type, name=name, attributes=attributes or {})
        return self.add_entity(entity)

    def get_entity(self, entity_id: UUID) -> Entity | None:
        with self._lock:
            return self._entities.get(entity_id)

    def find_by_name(self, name: str) -> Entity | None:
        with self._lock:
            eid = self._name_index.get(name.lower())
            return self._entities.get(eid) if eid else None

    def get_by_type(self, entity_type: EntityType) -> list[Entity]:
        with self._lock:
            ids = self._type_index.get(entity_type if isinstance(entity_type, str) else entity_type.value, [])
            return [self._entities[eid] for eid in ids if eid in self._entities]

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    def add_relationship(self, relationship: Relationship) -> Relationship:
        with self._lock:
            self._relationships[relationship.relationship_id] = relationship
            self._adjacency[relationship.source_entity_id].append(relationship.relationship_id)
        return relationship

    def relate(
        self,
        source_id: UUID,
        relationship_type: RelationshipType,
        target_id: UUID,
        attributes: dict[str, Any] | None = None,
        confidence: float = 100.0,
    ) -> Relationship:
        rel = Relationship(
            relationship_type=relationship_type,
            source_entity_id=source_id,
            target_entity_id=target_id,
            attributes=attributes or {},
            confidence=confidence,
        )
        return self.add_relationship(rel)

    def get_neighbors(
        self,
        entity_id: UUID,
        relationship_type: RelationshipType | None = None,
    ) -> list[Entity]:
        with self._lock:
            rel_ids = self._adjacency.get(entity_id, [])
            rels = [self._relationships[rid] for rid in rel_ids if rid in self._relationships]
            if relationship_type:
                rels = [r for r in rels if r.relationship_type == (relationship_type.value if hasattr(relationship_type, "value") else relationship_type)]
            return [
                self._entities[r.target_entity_id]
                for r in rels
                if r.target_entity_id in self._entities
            ]

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    @property
    def entity_count(self) -> int:
        with self._lock:
            return len(self._entities)

    @property
    def relationship_count(self) -> int:
        with self._lock:
            return len(self._relationships)
