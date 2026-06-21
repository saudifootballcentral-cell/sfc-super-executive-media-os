"""Tests for Social Knowledge Layer."""

from __future__ import annotations

import pytest

from sfc.social.knowledge.models import (
    EntityType,
    KnowledgeEntity,
    KnowledgeRelation,
    RelationType,
    SocialKnowledgeSnapshot,
)
from sfc.social.knowledge.service import SocialKnowledgeLayer, get_knowledge_layer


class TestEntityType:
    def test_eight_types(self):
        assert len(EntityType) == 8
        values = {t.value for t in EntityType}
        assert "narrative" in values
        assert "trend" in values
        assert "influencer" in values
        assert "player" in values
        assert "club" in values


class TestRelationType:
    def test_six_types(self):
        assert len(RelationType) == 6
        values = {t.value for t in RelationType}
        assert "influences" in values
        assert "supports" in values
        assert "opposes" in values
        assert "amplifies" in values
        assert "drives" in values
        assert "connected_to" in values


class TestKnowledgeEntity:
    def test_creation(self):
        e = KnowledgeEntity(
            entity_type=EntityType.TREND,
            name="Al Hilal Champions League",
        )
        assert e.entity_id != ""
        assert e.name == "Al Hilal Champions League"
        assert e.entity_type == EntityType.TREND

    def test_to_dict(self):
        e = KnowledgeEntity(
            entity_type=EntityType.PLAYER,
            name="Ronaldo",
            tags=["star", "transfer"],
        )
        d = e.to_dict()
        assert d["name"] == "Ronaldo"
        assert d["entity_type"] == "player"
        assert "star" in d["tags"]

    def test_properties_dict(self):
        e = KnowledgeEntity(
            entity_type=EntityType.CLUB,
            name="Al Nassr",
            properties={"league": "SPL", "founded": 1955},
        )
        assert e.properties["league"] == "SPL"


class TestKnowledgeRelation:
    def test_creation(self):
        r = KnowledgeRelation(
            source_id="entity_1",
            target_id="entity_2",
            relation_type=RelationType.INFLUENCES,
            strength=0.8,
        )
        assert r.relation_id != ""
        assert r.strength == 0.8

    def test_to_dict(self):
        r = KnowledgeRelation(
            source_id="a",
            target_id="b",
            relation_type=RelationType.AMPLIFIES,
            strength=0.5,
        )
        d = r.to_dict()
        assert d["relation_type"] == "amplifies"
        assert d["strength"] == 0.5


class TestSocialKnowledgeSnapshot:
    def test_defaults(self):
        s = SocialKnowledgeSnapshot()
        assert s.total_entities == 0
        assert s.total_relations == 0
        assert s.entities_by_type == {}

    def test_to_dict(self):
        s = SocialKnowledgeSnapshot(
            total_entities=5,
            total_relations=3,
        )
        d = s.to_dict()
        assert d["total_entities"] == 5
        assert d["total_relations"] == 3


class TestSocialKnowledgeLayer:
    def test_singleton(self):
        assert get_knowledge_layer() is get_knowledge_layer()

    def test_init(self):
        layer = SocialKnowledgeLayer()
        assert layer._entities == {}
        assert layer._relations == {}

    def test_add_entity(self):
        layer = SocialKnowledgeLayer()
        entity = layer.add_entity("Al Hilal", EntityType.CLUB)
        assert entity.name == "Al Hilal"
        assert entity.entity_type == EntityType.CLUB
        assert entity.entity_id in layer._entities

    def test_add_entity_with_properties(self):
        layer = SocialKnowledgeLayer()
        entity = layer.add_entity(
            "Transfer Saga",
            EntityType.NARRATIVE,
            properties={"score": 85.0},
            tags=["breaking", "transfer"],
        )
        assert entity.properties["score"] == 85.0
        assert "breaking" in entity.tags

    def test_add_entity_deduplicates_by_name(self):
        layer = SocialKnowledgeLayer()
        e1 = layer.add_entity("SPL", EntityType.COMPETITION)
        e2 = layer.add_entity("SPL", EntityType.COMPETITION, properties={"season": "2025"})
        assert e1.entity_id == e2.entity_id
        assert e2.properties.get("season") == "2025"

    def test_add_entity_case_insensitive_dedup(self):
        layer = SocialKnowledgeLayer()
        e1 = layer.add_entity("al hilal", EntityType.CLUB)
        e2 = layer.add_entity("Al Hilal", EntityType.CLUB)
        assert e1.entity_id == e2.entity_id

    def test_add_relation(self):
        layer = SocialKnowledgeLayer()
        e1 = layer.add_entity("Trend A", EntityType.TREND)
        e2 = layer.add_entity("Narrative B", EntityType.NARRATIVE)
        rel = layer.add_relation(e1.entity_id, e2.entity_id, RelationType.DRIVES)
        assert rel is not None
        assert rel.source_id == e1.entity_id
        assert rel.target_id == e2.entity_id

    def test_add_relation_invalid_entity_returns_none(self):
        layer = SocialKnowledgeLayer()
        result = layer.add_relation("bad_id", "also_bad", RelationType.INFLUENCES)
        assert result is None

    def test_add_relation_strength_clamped(self):
        layer = SocialKnowledgeLayer()
        e1 = layer.add_entity("A", EntityType.TOPIC)
        e2 = layer.add_entity("B", EntityType.TOPIC)
        rel = layer.add_relation(e1.entity_id, e2.entity_id, RelationType.SUPPORTS, strength=1.5)
        assert rel is not None
        assert rel.strength == 1.0

    def test_get_entity(self):
        layer = SocialKnowledgeLayer()
        entity = layer.add_entity("Ronaldo", EntityType.PLAYER)
        retrieved = layer.get_entity(entity.entity_id)
        assert retrieved is not None
        assert retrieved.name == "Ronaldo"

    def test_get_entity_unknown(self):
        layer = SocialKnowledgeLayer()
        assert layer.get_entity("nonexistent") is None

    def test_get_entities_by_type(self):
        layer = SocialKnowledgeLayer()
        layer.add_entity("Trend 1", EntityType.TREND)
        layer.add_entity("Trend 2", EntityType.TREND)
        layer.add_entity("Player A", EntityType.PLAYER)
        trends = layer.get_entities_by_type(EntityType.TREND)
        assert len(trends) == 2
        assert all(e.entity_type == EntityType.TREND for e in trends)

    def test_get_relations_for_entity(self):
        layer = SocialKnowledgeLayer()
        e1 = layer.add_entity("Source", EntityType.TREND)
        e2 = layer.add_entity("Target", EntityType.NARRATIVE)
        layer.add_relation(e1.entity_id, e2.entity_id, RelationType.INFLUENCES)
        rels = layer.get_relations_for_entity(e1.entity_id)
        assert len(rels) == 1

    def test_get_snapshot(self):
        layer = SocialKnowledgeLayer()
        layer.add_entity("E1", EntityType.TREND)
        layer.add_entity("E2", EntityType.CLUB)
        snapshot = layer.get_snapshot()
        assert snapshot.total_entities == 2
        assert snapshot.entities_by_type.get("trend") == 1
        assert snapshot.entities_by_type.get("club") == 1

    def test_snapshot_to_dict(self):
        layer = SocialKnowledgeLayer()
        layer.add_entity("Test", EntityType.TOPIC)
        snapshot = layer.get_snapshot()
        d = snapshot.to_dict()
        assert "total_entities" in d
        assert "entities_by_type" in d

    def test_ingest_from_trend(self):
        layer = SocialKnowledgeLayer()
        trend_data = {
            "topic": "Transfer window",
            "score": 88.0,
            "state": "hot",
            "hashtags": ["#transfer", "#SPL"],
        }
        entities = layer.ingest_from_trend(trend_data)
        assert len(entities) == 1
        assert entities[0].entity_type == EntityType.TREND

    def test_ingest_from_trend_empty_topic(self):
        layer = SocialKnowledgeLayer()
        entities = layer.ingest_from_trend({})
        assert entities == []

    def test_ingest_from_narrative(self):
        layer = SocialKnowledgeLayer()
        narrative_data = {
            "title": "Al Hilal dominance",
            "lifecycle": "peaking",
            "metrics": {"score": 90.0},
        }
        entities = layer.ingest_from_narrative(narrative_data)
        assert len(entities) == 1
        assert entities[0].entity_type == EntityType.NARRATIVE

    def test_build_relations_from_data(self):
        layer = SocialKnowledgeLayer()
        e1 = layer.add_entity("A", EntityType.TREND)
        e2 = layer.add_entity("B", EntityType.NARRATIVE)
        e3 = layer.add_entity("C", EntityType.TOPIC)
        rels = layer.build_relations_from_data(
            [e1.entity_id, e2.entity_id, e3.entity_id]
        )
        # 3 entities → 3 pairs
        assert len(rels) == 3

    def test_recent_additions_tracked(self):
        layer = SocialKnowledgeLayer()
        entity = layer.add_entity("New Entity", EntityType.INFLUENCER)
        assert entity.entity_id in layer._recent_additions
