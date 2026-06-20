"""Tests for KnowledgeGraphService."""

from __future__ import annotations

import pytest

from sfc.infrastructure.knowledge_graph.service import KnowledgeGraphService
from sfc.infrastructure.shared.types import ComponentHealth, HealthStatus


@pytest.fixture
def kg() -> KnowledgeGraphService:
    return KnowledgeGraphService()


@pytest.mark.asyncio
async def test_add_entity_returns_id(kg: KnowledgeGraphService) -> None:
    """add_entity() returns a non-empty entity_id string."""
    entity_id = await kg.add_entity("Cristiano Ronaldo", "player", {"nationality": "Portuguese"})
    assert isinstance(entity_id, str)
    assert len(entity_id) > 0


@pytest.mark.asyncio
async def test_add_entity_idempotent(kg: KnowledgeGraphService) -> None:
    """add_entity() for the same name returns the same entity_id."""
    id1 = await kg.add_entity("Al Hilal", "club")
    id2 = await kg.add_entity("Al Hilal", "club")
    assert id1 == id2


@pytest.mark.asyncio
async def test_add_relationship_success(kg: KnowledgeGraphService) -> None:
    """add_relationship() returns True when both entities exist."""
    await kg.add_entity("Cristiano Ronaldo", "player")
    await kg.add_entity("Al Nassr", "club")

    result = await kg.add_relationship("Cristiano Ronaldo", "Al Nassr", "plays_for")
    assert result is True


@pytest.mark.asyncio
async def test_add_relationship_missing_entity_returns_false(kg: KnowledgeGraphService) -> None:
    """add_relationship() returns False when an entity doesn't exist."""
    result = await kg.add_relationship("Unknown Player", "Al Hilal", "plays_for")
    assert result is False


@pytest.mark.asyncio
async def test_get_entity_profile_returns_profile(kg: KnowledgeGraphService) -> None:
    """get_entity_profile() returns a dict with expected fields."""
    await kg.add_entity("Salem Al-Dawsari", "player", {"position": "winger"})
    await kg.add_entity("Al Hilal", "club")
    await kg.add_relationship("Salem Al-Dawsari", "Al Hilal", "plays_for")

    profile = await kg.get_entity_profile("Salem Al-Dawsari")
    assert isinstance(profile, dict)
    assert profile["name"] == "Salem Al-Dawsari"
    assert profile["entity_type"] == "player"
    assert "relationships" in profile
    assert profile["relationship_count"] >= 1


@pytest.mark.asyncio
async def test_get_entity_profile_missing_returns_empty(kg: KnowledgeGraphService) -> None:
    """get_entity_profile() returns empty dict for unknown entities."""
    profile = await kg.get_entity_profile("Unknown Entity XYZ")
    assert profile == {}


@pytest.mark.asyncio
async def test_get_related_returns_neighbors(kg: KnowledgeGraphService) -> None:
    """get_related() returns entities related to the named entity."""
    await kg.add_entity("Roberto Firmino", "player")
    await kg.add_entity("Al Qadsiah", "club")
    await kg.add_relationship("Roberto Firmino", "Al Qadsiah", "plays_for")

    related = await kg.get_related("Roberto Firmino")
    assert len(related) >= 1
    names = [r["name"] for r in related]
    assert "Al Qadsiah" in names


@pytest.mark.asyncio
async def test_get_related_with_rel_type_filter(kg: KnowledgeGraphService) -> None:
    """get_related() filters by relationship type."""
    await kg.add_entity("Karim Benzema", "player")
    await kg.add_entity("Al Ittihad", "club")
    await kg.add_entity("Saudi Pro League", "competition")
    await kg.add_relationship("Karim Benzema", "Al Ittihad", "plays_for")
    await kg.add_relationship("Al Ittihad", "Saudi Pro League", "competes_in")

    # Get only plays_for relationships for Benzema
    related = await kg.get_related("Karim Benzema", rel_type="plays_for")
    names = [r["name"] for r in related]
    assert "Al Ittihad" in names


@pytest.mark.asyncio
async def test_get_sponsor_map(kg: KnowledgeGraphService) -> None:
    """get_sponsor_map() returns sponsors for an entity."""
    await kg.add_entity("Al Nassr", "club")
    await kg.add_entity("STC", "sponsor")
    await kg.add_relationship("Al Nassr", "STC", "sponsored_by")

    sponsors = await kg.get_sponsor_map("Al Nassr")
    assert isinstance(sponsors, list)
    assert len(sponsors) >= 1
    sponsor_names = [s["sponsor_name"] for s in sponsors]
    assert "STC" in sponsor_names


@pytest.mark.asyncio
async def test_get_sponsor_map_no_sponsors(kg: KnowledgeGraphService) -> None:
    """get_sponsor_map() returns empty list when no sponsors exist."""
    await kg.add_entity("Small Club", "club")
    sponsors = await kg.get_sponsor_map("Small Club")
    assert sponsors == []


@pytest.mark.asyncio
async def test_query_by_entity_type(kg: KnowledgeGraphService) -> None:
    """query() filters by entity type."""
    await kg.add_entity("Player One", "player")
    await kg.add_entity("Player Two", "player")
    await kg.add_entity("Big Club", "club")

    players = await kg.query(entity_type="player")
    clubs = await kg.query(entity_type="club")

    player_names = [p["name"] for p in players]
    club_names = [c["name"] for c in clubs]

    assert "Player One" in player_names
    assert "Player Two" in player_names
    assert "Big Club" in club_names
    # Players should not appear in clubs
    assert "Player One" not in club_names


@pytest.mark.asyncio
async def test_ingest_intelligence_report_extracts_entities(kg: KnowledgeGraphService) -> None:
    """ingest_intelligence_report() extracts entities from report dict."""
    report = {
        "key_players": ["Cristiano Ronaldo", "Sadio Mane"],
        "clubs_mentioned": ["Al Nassr", "Al Hilal"],
        "competitions": ["Saudi Pro League"],
        "entities": [
            {"name": "Roberto Firmino", "type": "player", "properties": {"goals": 5}},
        ],
    }

    count = await kg.ingest_intelligence_report(report)
    assert count >= 5  # 2 players + 2 clubs + 1 competition + 1 entity

    # Verify entities were added
    ronaldo = kg._graph.find_by_name("Cristiano Ronaldo")
    assert ronaldo is not None


@pytest.mark.asyncio
async def test_ingest_empty_report(kg: KnowledgeGraphService) -> None:
    """ingest_intelligence_report() handles empty report gracefully."""
    count = await kg.ingest_intelligence_report({})
    assert count == 0


@pytest.mark.asyncio
async def test_get_influence_network(kg: KnowledgeGraphService) -> None:
    """get_influence_network() returns nodes and edges."""
    await kg.add_entity("Coach X", "coach")
    await kg.add_entity("Club A", "club")
    await kg.add_entity("Player Y", "player")
    await kg.add_relationship("Coach X", "Club A", "coaches")
    await kg.add_relationship("Player Y", "Club A", "plays_for")

    network = await kg.get_influence_network("Coach X", depth=2)
    assert "center" in network
    assert "nodes" in network
    assert "edges" in network
    assert network["center"] == "Coach X"


def test_health_check_returns_component_health(kg: KnowledgeGraphService) -> None:
    """health_check() returns ComponentHealth without raising."""
    health = kg.health_check()
    assert isinstance(health, ComponentHealth)
    assert health.component == "knowledge_graph"
    assert health.status in list(HealthStatus)


def test_health_check_never_raises(kg: KnowledgeGraphService) -> None:
    """health_check() must never raise."""
    health = kg.health_check()
    assert health is not None
