"""Social Knowledge Layer — persistent knowledge graph for social intelligence."""

from __future__ import annotations

import logging
from typing import Any

from sfc.social.knowledge.models import (
    EntityType,
    KnowledgeEntity,
    KnowledgeRelation,
    RelationType,
    SocialKnowledgeSnapshot,
)

logger = logging.getLogger("sfc.social.knowledge")

_singleton: "SocialKnowledgeLayer | None" = None


def get_knowledge_layer() -> "SocialKnowledgeLayer":
    global _singleton
    if _singleton is None:
        _singleton = SocialKnowledgeLayer()
    return _singleton


class SocialKnowledgeLayer:
    """Knowledge graph for persisting social intelligence entities and relations."""

    def __init__(self) -> None:
        self._entities: dict[str, KnowledgeEntity] = {}
        self._relations: dict[str, KnowledgeRelation] = {}
        self._recent_additions: list[str] = []
        self._max_recent = 50

    def add_entity(
        self,
        name: str,
        entity_type: EntityType,
        properties: dict[str, Any] | None = None,
        tags: list[str] | None = None,
    ) -> KnowledgeEntity:
        """Add or update an entity in the knowledge graph."""
        existing = self._find_entity_by_name(name)
        if existing:
            if properties:
                existing.properties.update(properties)
            if tags:
                existing.tags = list(set(existing.tags + tags))
            from datetime import datetime
            existing.updated_at = datetime.utcnow()
            return existing

        entity = KnowledgeEntity(
            entity_type=entity_type,
            name=name,
            properties=properties or {},
            tags=tags or [],
        )
        self._entities[entity.entity_id] = entity
        self._track_addition(entity.entity_id)
        logger.debug("[Knowledge] Added entity: %s (%s)", name, entity_type.value)
        return entity

    def add_relation(
        self,
        source_id: str,
        target_id: str,
        relation_type: RelationType,
        strength: float = 0.5,
        evidence: str = "",
    ) -> KnowledgeRelation | None:
        """Add a relation between two entities."""
        if source_id not in self._entities or target_id not in self._entities:
            logger.warning(
                "[Knowledge] Cannot add relation — entity not found: %s -> %s",
                source_id,
                target_id,
            )
            return None

        relation = KnowledgeRelation(
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            strength=max(0.0, min(1.0, strength)),
            evidence=evidence,
        )
        self._relations[relation.relation_id] = relation
        return relation

    def get_entity(self, entity_id: str) -> KnowledgeEntity | None:
        return self._entities.get(entity_id)

    def get_entities_by_type(self, entity_type: EntityType) -> list[KnowledgeEntity]:
        return [e for e in self._entities.values() if e.entity_type == entity_type]

    def get_relations_for_entity(
        self, entity_id: str
    ) -> list[KnowledgeRelation]:
        return [
            r for r in self._relations.values()
            if r.source_id == entity_id or r.target_id == entity_id
        ]

    def get_snapshot(self) -> SocialKnowledgeSnapshot:
        """Return a snapshot of the current knowledge graph state."""
        entities_by_type: dict[str, int] = {}
        for entity in self._entities.values():
            key = entity.entity_type.value
            entities_by_type[key] = entities_by_type.get(key, 0) + 1

        relations_by_type: dict[str, int] = {}
        for relation in self._relations.values():
            key = relation.relation_type.value
            relations_by_type[key] = relations_by_type.get(key, 0) + 1

        top_entities = [
            {"entity_id": e.entity_id, "name": e.name, "type": e.entity_type.value}
            for e in list(self._entities.values())[:10]
        ]

        return SocialKnowledgeSnapshot(
            total_entities=len(self._entities),
            total_relations=len(self._relations),
            entities_by_type=entities_by_type,
            relations_by_type=relations_by_type,
            top_entities=top_entities,
            recent_additions=list(self._recent_additions),
        )

    def ingest_from_trend(self, trend_data: dict[str, Any]) -> list[KnowledgeEntity]:
        """Ingest entities from a trend report."""
        entities = []
        topic = trend_data.get("topic", "")
        if topic:
            entity = self.add_entity(
                name=topic,
                entity_type=EntityType.TREND,
                properties={
                    "score": trend_data.get("score", 0),
                    "state": trend_data.get("state", ""),
                },
                tags=trend_data.get("hashtags", []),
            )
            entities.append(entity)
        return entities

    def ingest_from_narrative(self, narrative_data: dict[str, Any]) -> list[KnowledgeEntity]:
        """Ingest entities from a narrative report."""
        entities = []
        title = narrative_data.get("title", "")
        if title:
            entity = self.add_entity(
                name=title,
                entity_type=EntityType.NARRATIVE,
                properties={
                    "lifecycle": narrative_data.get("lifecycle", ""),
                    "score": narrative_data.get("metrics", {}).get("score", 0),
                },
            )
            entities.append(entity)
        return entities

    def build_relations_from_data(
        self, entity_ids: list[str], relation_type: RelationType = RelationType.CONNECTED_TO
    ) -> list[KnowledgeRelation]:
        """Build relations between a list of entities."""
        relations = []
        for i, src in enumerate(entity_ids):
            for tgt in entity_ids[i + 1:]:
                rel = self.add_relation(src, tgt, relation_type, strength=0.6)
                if rel:
                    relations.append(rel)
        return relations

    def _find_entity_by_name(self, name: str) -> KnowledgeEntity | None:
        for entity in self._entities.values():
            if entity.name.lower() == name.lower():
                return entity
        return None

    def _track_addition(self, entity_id: str) -> None:
        self._recent_additions.append(entity_id)
        if len(self._recent_additions) > self._max_recent:
            self._recent_additions = self._recent_additions[-self._max_recent:]
