"""Knowledge Graph — in-memory graph store with entity and relationship management."""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any
from uuid import UUID

from core.knowledge_graph.entities import Entity, EntityType
from core.knowledge_graph.relationships import Relationship, RelationshipType

logger = logging.getLogger("sfc.knowledge_graph")


class KnowledgeGraph:
    """Directed property graph for Saudi football domain knowledge.

    Example:
        Salem AlDossari → plays_for → Al Hilal
        Al Hilal → competes_in → Saudi Pro League
        Saudi Pro League → governed_by → SAFF
    """

    def __init__(self) -> None:
        self._entities: dict[UUID, Entity] = {}
        self._relationships: dict[UUID, Relationship] = {}
        self._name_index: dict[str, UUID] = {}
        self._type_index: dict[EntityType, list[UUID]] = defaultdict(list)
        self._adjacency: dict[UUID, list[UUID]] = defaultdict(list)

    # ------------------------------------------------------------------
    # Entities
    # ------------------------------------------------------------------

    def add_entity(self, entity: Entity) -> Entity:
        self._entities[entity.entity_id] = entity
        self._name_index[entity.name.lower()] = entity.entity_id
        for alias in entity.aliases:
            self._name_index[alias.lower()] = entity.entity_id
        self._type_index[EntityType(entity.entity_type)].append(entity.entity_id)
        logger.debug("[KG] Added entity %s (%s)", entity.name, entity.entity_type)
        return entity

    def get_entity(self, entity_id: UUID) -> Entity | None:
        return self._entities.get(entity_id)

    def find_by_name(self, name: str) -> Entity | None:
        eid = self._name_index.get(name.lower())
        return self._entities.get(eid) if eid else None

    def get_by_type(self, entity_type: EntityType) -> list[Entity]:
        ids = self._type_index.get(entity_type, [])
        return [self._entities[eid] for eid in ids if eid in self._entities]

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    def add_relationship(self, relationship: Relationship) -> Relationship:
        self._relationships[relationship.relationship_id] = relationship
        self._adjacency[relationship.source_entity_id].append(relationship.relationship_id)
        logger.debug(
            "[KG] Added relationship %s —[%s]→ %s",
            relationship.source_entity_id,
            relationship.relationship_type,
            relationship.target_entity_id,
        )
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

    def get_outgoing(
        self,
        entity_id: UUID,
        relationship_type: RelationshipType | None = None,
    ) -> list[Relationship]:
        rel_ids = self._adjacency.get(entity_id, [])
        rels = [self._relationships[rid] for rid in rel_ids if rid in self._relationships]
        if relationship_type:
            rels = [r for r in rels if r.relationship_type == relationship_type]
        return rels

    def get_neighbors(
        self,
        entity_id: UUID,
        relationship_type: RelationshipType | None = None,
    ) -> list[Entity]:
        rels = self.get_outgoing(entity_id, relationship_type)
        return [
            self._entities[r.target_entity_id]
            for r in rels
            if r.target_entity_id in self._entities
        ]

    def path_exists(self, source_id: UUID, target_id: UUID, max_depth: int = 5) -> bool:
        visited: set[UUID] = set()
        queue = [source_id]
        depth = 0
        while queue and depth < max_depth:
            next_queue: list[UUID] = []
            for eid in queue:
                if eid == target_id:
                    return True
                if eid in visited:
                    continue
                visited.add(eid)
                for rel in self.get_outgoing(eid):
                    next_queue.append(rel.target_entity_id)
            queue = next_queue
            depth += 1
        return False

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    @property
    def entity_count(self) -> int:
        return len(self._entities)

    @property
    def relationship_count(self) -> int:
        return len(self._relationships)
