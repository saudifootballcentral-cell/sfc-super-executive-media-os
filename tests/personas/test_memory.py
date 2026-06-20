"""Tests for PersonaMemoryLayer."""
from __future__ import annotations

from sfc.events.bus import get_event_bus
from sfc.personas.memory.service import PersonaMemoryLayer
from sfc.personas.memory.models import MemoryNamespace


class TestPersonaMemoryLayer:
    def setup_method(self):
        get_event_bus().reset()

    async def test_save_and_load_snapshot(self):
        memory = PersonaMemoryLayer()
        content = {"key": "value", "match": "Al-Hilal vs Al-Nassr"}
        snapshot = await memory.save_snapshot(
            "PERSONA-JOURNALIST-01", MemoryNamespace.WORKING, content
        )
        assert snapshot.persona_id == "PERSONA-JOURNALIST-01"
        assert snapshot.namespace == MemoryNamespace.WORKING

        loaded = await memory.load_snapshot("PERSONA-JOURNALIST-01", MemoryNamespace.WORKING)
        assert loaded is not None
        assert loaded.content == content

    async def test_record_learning(self):
        memory = PersonaMemoryLayer()
        record = await memory.record_learning(
            "PERSONA-ANALYST-01",
            lesson="Match statistics improve engagement by 40%",
            context={"source": "experiment_001"},
        )
        assert record.persona_id == "PERSONA-ANALYST-01"
        assert "engagement" in record.lesson

    async def test_assemble_context(self):
        memory = PersonaMemoryLayer()
        await memory.save_snapshot(
            "PERSONA-CREATIVE-01", MemoryNamespace.GLOBAL, {"brand": "SFC"}
        )
        await memory.record_learning(
            "PERSONA-CREATIVE-01", "Visual content drives 3x more shares"
        )
        package = await memory.assemble_context("PERSONA-CREATIVE-01", "campaign")
        assert package.persona_id == "PERSONA-CREATIVE-01"
        assert package.task_type == "campaign"
        assert len(package.snapshots) == 1
        assert len(package.active_learnings) == 1

    async def test_get_state_creates_new(self):
        memory = PersonaMemoryLayer()
        state = await memory.get_state("PERSONA-NEW-01")
        assert state.persona_id == "PERSONA-NEW-01"
        assert state.knowledge_snapshot == {}
        assert state.learning_records == []

    def test_health_check(self):
        memory = PersonaMemoryLayer()
        health = memory.health_check()
        assert health["status"] == "healthy"
        assert health["component"] == "PersonaMemoryLayer"
