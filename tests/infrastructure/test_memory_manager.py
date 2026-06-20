"""Tests for MemoryManagerService."""

from __future__ import annotations

import pytest

from sfc.infrastructure.memory_manager.service import MemoryManagerService
from sfc.infrastructure.shared.types import ComponentHealth, HealthStatus


@pytest.fixture
def memory() -> MemoryManagerService:
    return MemoryManagerService()


@pytest.mark.asyncio
async def test_store_and_retrieve_global(memory: MemoryManagerService) -> None:
    """store() and retrieve() round-trip in global memory."""
    await memory.store("players", "cr7", {"name": "Cristiano Ronaldo", "club": "Al Nassr"})
    result = await memory.retrieve("players", "cr7")
    assert result is not None
    assert result["name"] == "Cristiano Ronaldo"


@pytest.mark.asyncio
async def test_store_and_retrieve_division(memory: MemoryManagerService) -> None:
    """store() and retrieve() round-trip in division memory."""
    await memory.store("drafts", "article-001", {"title": "SPL Match Report"}, division="editorial")
    result = await memory.retrieve("drafts", "article-001", division="editorial")
    assert result is not None
    assert result["title"] == "SPL Match Report"


@pytest.mark.asyncio
async def test_retrieve_missing_key_returns_none(memory: MemoryManagerService) -> None:
    """retrieve() returns None for missing keys."""
    result = await memory.retrieve("players", "nonexistent_player")
    assert result is None


@pytest.mark.asyncio
async def test_update_overwrites_existing(memory: MemoryManagerService) -> None:
    """update() overwrites an existing entry."""
    await memory.store("clubs", "alhilal", {"trophies": 10})
    await memory.update("clubs", "alhilal", {"trophies": 11})
    result = await memory.retrieve("clubs", "alhilal")
    assert result["trophies"] == 11


@pytest.mark.asyncio
async def test_search_by_keyword_in_key(memory: MemoryManagerService) -> None:
    """search() finds entries where the keyword matches the key."""
    await memory.store("players", "ronaldo_cr7", {"goals": 900})
    await memory.store("players", "messi_lm10", {"goals": 800})

    results = await memory.search("ronaldo")
    assert len(results) >= 1
    assert any("ronaldo" in r["key"] for r in results)


@pytest.mark.asyncio
async def test_search_by_keyword_in_value(memory: MemoryManagerService) -> None:
    """search() finds entries where the keyword matches the value."""
    await memory.store("players", "player_001", "Cristiano Ronaldo profile")
    results = await memory.search("Cristiano")
    assert len(results) >= 1


@pytest.mark.asyncio
async def test_search_namespace_filter(memory: MemoryManagerService) -> None:
    """search() with namespace filter only returns from that namespace."""
    await memory.store("players", "cr7", {"name": "Ronaldo"})
    await memory.store("clubs", "alhilal", {"name": "Al Hilal"})

    results = await memory.search("al", namespace="clubs")
    assert all(r["namespace"] == "clubs" for r in results)


@pytest.mark.asyncio
async def test_record_episode(memory: MemoryManagerService) -> None:
    """record_episode() stores an episode in episodic memory."""
    await memory.record_episode(
        run_id="run-test-001",
        event="Transfer news processed",
        decision="Publish immediately",
        result="4.2M reach achieved",
        lesson="Breaking news at 8pm drives maximum engagement",
        division="intelligence",
    )
    # Verify the episodic memory received it
    episodes = memory._episodic.get_by_run("run-test-001")
    assert len(episodes) == 1
    assert episodes[0].lesson == "Breaking news at 8pm drives maximum engagement"


@pytest.mark.asyncio
async def test_record_episode_no_division(memory: MemoryManagerService) -> None:
    """record_episode() works without a division."""
    await memory.record_episode(
        run_id="run-test-002",
        event="Analysis complete",
        decision="Archive",
        result="Data stored",
        lesson="No specific lesson",
        division=None,
    )
    episodes = memory._episodic.get_by_run("run-test-002")
    assert len(episodes) == 1


def test_get_division_memory_same_instance(memory: MemoryManagerService) -> None:
    """get_division_memory() returns the same instance for the same division."""
    mem1 = memory.get_division_memory("editorial")
    mem2 = memory.get_division_memory("editorial")
    assert mem1 is mem2


def test_get_division_memory_different_divisions(memory: MemoryManagerService) -> None:
    """get_division_memory() returns different instances for different divisions."""
    editorial_mem = memory.get_division_memory("editorial")
    intelligence_mem = memory.get_division_memory("intelligence")
    assert editorial_mem is not intelligence_mem


def test_get_division_memory_unknown_division(memory: MemoryManagerService) -> None:
    """get_division_memory() handles unknown division names gracefully."""
    mem = memory.get_division_memory("custom_division")
    assert mem is not None


@pytest.mark.asyncio
async def test_archive(memory: MemoryManagerService) -> None:
    """archive() moves entry to cold storage."""
    await memory.store("players", "old_player", {"retired": True})
    await memory.archive("players", "old_player")

    # Should no longer be in global memory
    result = await memory.retrieve("players", "old_player")
    assert result is None

    # Should be in archive
    assert "players" in memory._archive
    assert "old_player" in memory._archive["players"]


@pytest.mark.asyncio
async def test_expire(memory: MemoryManagerService) -> None:
    """expire() deletes entry from memory."""
    await memory.store("temp", "temp_key", "temp_value")
    await memory.expire("temp", "temp_key")

    result = await memory.retrieve("temp", "temp_key")
    assert result is None


@pytest.mark.asyncio
async def test_summarize(memory: MemoryManagerService) -> None:
    """summarize() returns a human-readable summary."""
    await memory.store("analytics", "reach_2024", 4_200_000)
    await memory.store("analytics", "engagement_rate", 0.12)

    summary = await memory.summarize("analytics")
    assert isinstance(summary, str)
    assert "analytics" in summary.lower()


@pytest.mark.asyncio
async def test_summarize_empty_namespace(memory: MemoryManagerService) -> None:
    """summarize() handles empty namespaces gracefully."""
    summary = await memory.summarize("empty_namespace_xyz")
    assert "empty" in summary.lower()


def test_health_check_returns_component_health(memory: MemoryManagerService) -> None:
    """health_check() returns ComponentHealth without raising."""
    health = memory.health_check()
    assert isinstance(health, ComponentHealth)
    assert health.component == "memory_manager"
    assert health.status in list(HealthStatus)
    assert "global_entries" in health.metrics


def test_health_check_never_raises(memory: MemoryManagerService) -> None:
    """health_check() must never raise."""
    health = memory.health_check()
    assert health is not None
