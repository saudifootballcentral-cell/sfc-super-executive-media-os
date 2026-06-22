"""Knowledge Graph Service — wraps sfc.knowledge_graph with richer query capabilities."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sfc.knowledge_graph.graph import KnowledgeGraph
from sfc.knowledge_graph.entities import Entity, EntityType
from sfc.knowledge_graph.relationships import Relationship, RelationshipType
from sfc.infrastructure.shared.types import ComponentHealth, HealthStatus
from sfc.infrastructure.knowledge_graph.models import (
    EntityProfile,
    RelationshipMap,
    KGQuery,
    KGQueryResult,
)

logger = logging.getLogger("sfc.infrastructure.knowledge_graph")

# Mapping from string names to EntityType values (case-insensitive)
_ENTITY_TYPE_MAP: dict[str, EntityType] = {
    "player": EntityType.PLAYER,
    "club": EntityType.CLUB,
    "coach": EntityType.COACH,
    "competition": EntityType.COMPETITION,
    "match": EntityType.MATCH,
    "sponsor": EntityType.SPONSOR,
    "journalist": EntityType.JOURNALIST,
    "content": EntityType.CONTENT,
    "campaign": EntityType.CAMPAIGN,
    "brand": EntityType.BRAND,
    "tournament": EntityType.TOURNAMENT,
    # aliases
    "venue": EntityType.CONTENT,         # fallback
    "federation": EntityType.COMPETITION, # fallback
}

# Mapping from string names to RelationshipType values
_REL_TYPE_MAP: dict[str, RelationshipType] = {
    "plays_for": RelationshipType.PLAYS_FOR,
    "played_for": RelationshipType.PLAYS_FOR,
    "coaches": RelationshipType.COACHES,
    "managed_by": RelationshipType.MANAGES,
    "competes_in": RelationshipType.COMPETES_IN,
    "participated_in": RelationshipType.PARTICIPATED_IN,
    "sponsored_by": RelationshipType.SPONSORED_BY,
    "reported_by": RelationshipType.REPORTED_BY,
    "related_to": RelationshipType.RELATED_TO,
    "created": RelationshipType.CREATED,
    "owns": RelationshipType.OWNS,
    "supports": RelationshipType.RELATED_TO,
    "opposes": RelationshipType.RELATED_TO,
    "influences": RelationshipType.RELATED_TO,
}


class KnowledgeGraphService:
    """Wraps KnowledgeGraph with richer query and ingestion capabilities."""

    def __init__(self) -> None:
        self._graph: KnowledgeGraph = KnowledgeGraph()

    async def add_entity(
        self,
        name: str,
        entity_type: str,
        properties: dict[str, Any] | None = None,
    ) -> str:
        """Add entity, return entity_id string."""
        et = _ENTITY_TYPE_MAP.get(entity_type.lower(), EntityType.CONTENT)
        entity = self._graph.upsert_entity(et, name, properties or {})
        logger.debug("[KGService] Entity added: %s (%s)", name, entity_type)
        return str(entity.entity_id)

    async def add_relationship(
        self,
        from_name: str,
        to_name: str,
        rel_type: str,
        properties: dict[str, Any] | None = None,
    ) -> bool:
        """Add relationship between entities by name."""
        source = self._graph.find_by_name(from_name)
        target = self._graph.find_by_name(to_name)

        if source is None or target is None:
            logger.warning(
                "[KGService] Cannot add relationship %s->%s: entity not found",
                from_name, to_name,
            )
            return False

        rt = _REL_TYPE_MAP.get(rel_type.lower(), RelationshipType.RELATED_TO)
        self._graph.relate(source.entity_id, rt, target.entity_id, properties or {})
        logger.debug("[KGService] Relationship: %s -[%s]-> %s", from_name, rel_type, to_name)
        return True

    async def get_entity_profile(self, name: str) -> dict[str, Any]:
        """Full profile: entity + all relationships."""
        entity = self._graph.find_by_name(name)
        if entity is None:
            return {}

        # Get all relationships
        relationships: list[dict[str, Any]] = []
        for rel in self._graph._relationships.values():
            if rel.source_entity_id == entity.entity_id:
                target = self._graph.get_entity(rel.target_entity_id)
                if target:
                    relationships.append({
                        "type": rel.relationship_type,
                        "direction": "outgoing",
                        "target_name": target.name,
                        "target_type": target.entity_type,
                        "confidence": rel.confidence,
                        "attributes": rel.attributes,
                    })
            elif rel.target_entity_id == entity.entity_id:
                source = self._graph.get_entity(rel.source_entity_id)
                if source:
                    relationships.append({
                        "type": rel.relationship_type,
                        "direction": "incoming",
                        "source_name": source.name,
                        "source_type": source.entity_type,
                        "confidence": rel.confidence,
                        "attributes": rel.attributes,
                    })

        profile = EntityProfile(
            entity_id=str(entity.entity_id),
            name=entity.name,
            entity_type=entity.entity_type,
            properties=entity.attributes,
            relationships=relationships,
            relationship_count=len(relationships),
        )
        return profile.model_dump()

    async def get_related(
        self,
        name: str,
        rel_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get entities related to name."""
        entity = self._graph.find_by_name(name)
        if entity is None:
            return []

        rt = None
        if rel_type:
            rt = _REL_TYPE_MAP.get(rel_type.lower())

        neighbors = self._graph.get_neighbors(entity.entity_id, rt)
        return [
            {
                "entity_id": str(n.entity_id),
                "name": n.name,
                "entity_type": n.entity_type,
                "attributes": n.attributes,
            }
            for n in neighbors
        ]

    async def get_influence_network(
        self,
        name: str,
        depth: int = 2,
    ) -> dict[str, Any]:
        """Traverse influence relationships up to depth hops."""
        visited: set[str] = set()
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []

        async def traverse(entity_name: str, current_depth: int) -> None:
            if current_depth > depth or entity_name in visited:
                return
            visited.add(entity_name)
            entity = self._graph.find_by_name(entity_name)
            if entity is None:
                return
            nodes.append({
                "name": entity.name,
                "type": entity.entity_type,
                "depth": depth - current_depth,
            })
            neighbors = self._graph.get_neighbors(entity.entity_id)
            for neighbor in neighbors:
                edges.append({"from": entity_name, "to": neighbor.name})
                await traverse(neighbor.name, current_depth + 1)

        await traverse(name, 0)
        return {"center": name, "nodes": nodes, "edges": edges, "depth": depth}

    async def get_sponsor_map(self, entity_name: str) -> list[dict[str, Any]]:
        """Find all sponsors related to an entity."""
        entity = self._graph.find_by_name(entity_name)
        if entity is None:
            return []

        sponsors: list[dict[str, Any]] = []
        for rel in self._graph._relationships.values():
            # Check if this is a sponsored_by relationship involving our entity
            if rel.relationship_type == RelationshipType.SPONSORED_BY.value:
                if rel.source_entity_id == entity.entity_id:
                    sponsor = self._graph.get_entity(rel.target_entity_id)
                    if sponsor:
                        sponsors.append({
                            "sponsor_name": sponsor.name,
                            "sponsor_type": sponsor.entity_type,
                            "confidence": rel.confidence,
                            "attributes": rel.attributes,
                        })
            # Also check OWNS relationships pointing to the entity
            elif rel.relationship_type == RelationshipType.OWNS.value:
                if rel.target_entity_id == entity.entity_id:
                    owner = self._graph.get_entity(rel.source_entity_id)
                    if owner and owner.entity_type in (
                        EntityType.SPONSOR.value, EntityType.BRAND.value
                    ):
                        sponsors.append({
                            "sponsor_name": owner.name,
                            "sponsor_type": owner.entity_type,
                            "confidence": rel.confidence,
                            "attributes": rel.attributes,
                        })

        return sponsors

    async def query(
        self,
        entity_type: str | None = None,
        rel_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Flexible query by type filters."""
        results: list[dict[str, Any]] = []

        if entity_type:
            et = _ENTITY_TYPE_MAP.get(entity_type.lower())
            if et:
                entities = self._graph.get_by_type(et)
                for entity in entities:
                    results.append({
                        "entity_id": str(entity.entity_id),
                        "name": entity.name,
                        "entity_type": entity.entity_type,
                        "attributes": entity.attributes,
                    })
        else:
            # Return all entities
            for entity in self._graph._entities.values():
                results.append({
                    "entity_id": str(entity.entity_id),
                    "name": entity.name,
                    "entity_type": entity.entity_type,
                    "attributes": entity.attributes,
                })

        # Filter by relationship type if specified
        if rel_type:
            rt_str = _REL_TYPE_MAP.get(rel_type.lower(), RelationshipType.RELATED_TO).value
            entity_ids_with_rel: set[str] = set()
            for rel in self._graph._relationships.values():
                if rel.relationship_type == rt_str:
                    entity_ids_with_rel.add(str(rel.source_entity_id))
                    entity_ids_with_rel.add(str(rel.target_entity_id))
            results = [r for r in results if r["entity_id"] in entity_ids_with_rel]

        return results

    async def ingest_intelligence_report(self, report: dict[str, Any]) -> int:
        """Auto-extract entities from an intelligence report. Returns entity count."""
        count = 0

        # Extract entities from well-known report fields
        entities_data = report.get("entities", [])
        for entity_data in entities_data:
            if isinstance(entity_data, dict):
                name = entity_data.get("name", "")
                entity_type = entity_data.get("type", "content")
                properties = entity_data.get("properties", {})
                if name:
                    await self.add_entity(name, entity_type, properties)
                    count += 1

        # Extract from mentions
        mentions = report.get("key_players", [])
        for mention in mentions:
            if isinstance(mention, str):
                await self.add_entity(mention, "player", {})
                count += 1
            elif isinstance(mention, dict) and mention.get("name"):
                await self.add_entity(
                    mention["name"],
                    mention.get("type", "player"),
                    mention.get("attributes", {}),
                )
                count += 1

        # Extract clubs
        clubs = report.get("clubs_mentioned", [])
        for club in clubs:
            if isinstance(club, str):
                await self.add_entity(club, "club", {})
                count += 1

        # Extract competitions
        competitions = report.get("competitions", [])
        for comp in competitions:
            if isinstance(comp, str):
                await self.add_entity(comp, "competition", {})
                count += 1

        # Extract relationships from report
        relationships = report.get("relationships", [])
        for rel_data in relationships:
            if isinstance(rel_data, dict):
                await self.add_relationship(
                    rel_data.get("from", ""),
                    rel_data.get("to", ""),
                    rel_data.get("type", "related_to"),
                    rel_data.get("properties", {}),
                )

        logger.info("[KGService] Ingested %d entities from intelligence report", count)
        return count

    def health_check(self) -> ComponentHealth:
        """Return health status of the knowledge graph service."""
        try:
            return ComponentHealth(
                component="knowledge_graph",
                status=HealthStatus.HEALTHY,
                last_check=datetime.utcnow(),
                metrics={
                    "entity_count": self._graph.entity_count,
                    "relationship_count": self._graph.relationship_count,
                },
            )
        except Exception as exc:  # noqa: BLE001
            return ComponentHealth(
                component="knowledge_graph",
                status=HealthStatus.UNHEALTHY,
                last_check=datetime.utcnow(),
                metrics={},
                errors=[str(exc)],
            )


def get_knowledge_graph() -> KnowledgeGraphService:
    """Return the process-wide KnowledgeGraphService from InfrastructureContext."""
    from sfc.infrastructure.context import get_infrastructure  # lazy — avoids circular import
    return get_infrastructure().knowledge_graph
