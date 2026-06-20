from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sfc.personas.shared.types import PersonaMemoryState
from sfc.personas.memory.models import (
    ContextPackage,
    KnowledgeSnapshot,
    LearningRecord,
    MemoryNamespace,
)

logger = logging.getLogger("sfc.personas.memory")


class PersonaMemoryLayer:
    """Lightweight in-memory store for persona knowledge and learnings."""

    def __init__(self) -> None:
        self._store: dict[str, PersonaMemoryState] = {}
        self._snapshots: dict[str, list[KnowledgeSnapshot]] = {}
        self._learnings: dict[str, list[LearningRecord]] = {}

    async def get_state(self, persona_id: str) -> PersonaMemoryState:
        """Return existing state or create new one."""
        if persona_id not in self._store:
            self._store[persona_id] = PersonaMemoryState(persona_id=persona_id)
        return self._store[persona_id]

    async def save_snapshot(
        self, persona_id: str, namespace: MemoryNamespace, content: dict[str, Any]
    ) -> KnowledgeSnapshot:
        """Save a knowledge snapshot for a persona."""
        snapshot = KnowledgeSnapshot(
            persona_id=persona_id,
            namespace=namespace,
            content=content,
        )
        if persona_id not in self._snapshots:
            self._snapshots[persona_id] = []
        self._snapshots[persona_id].append(snapshot)

        # Update memory state
        state = await self.get_state(persona_id)
        state_data = state.model_dump()
        state_data["knowledge_snapshot"][namespace.value] = content
        state_data["last_updated"] = datetime.utcnow()
        self._store[persona_id] = PersonaMemoryState(**state_data)

        logger.debug("[PersonaMemoryLayer] Saved snapshot for %s in namespace %s", persona_id, namespace.value)
        return snapshot

    async def load_snapshot(
        self, persona_id: str, namespace: MemoryNamespace
    ) -> KnowledgeSnapshot | None:
        """Return latest snapshot for the given namespace."""
        snapshots = self._snapshots.get(persona_id, [])
        matching = [s for s in snapshots if s.namespace == namespace]
        return matching[-1] if matching else None

    async def record_learning(
        self, persona_id: str, lesson: str, context: dict[str, Any] | None = None
    ) -> LearningRecord:
        """Record a learning for a persona."""
        if context is None:
            context = {}
        record = LearningRecord(
            persona_id=persona_id,
            lesson=lesson,
            context=context,
        )
        if persona_id not in self._learnings:
            self._learnings[persona_id] = []
        self._learnings[persona_id].append(record)

        # Update memory state
        state = await self.get_state(persona_id)
        state_data = state.model_dump()
        state_data["learning_records"].append({"lesson": lesson, "context": context})
        state_data["last_updated"] = datetime.utcnow()
        self._store[persona_id] = PersonaMemoryState(**state_data)

        logger.debug("[PersonaMemoryLayer] Recorded learning for %s: %s", persona_id, lesson)
        return record

    async def assemble_context(self, persona_id: str, task_type: str) -> ContextPackage:
        """Gather all snapshots and learnings for a persona."""
        snapshots = list(self._snapshots.get(persona_id, []))
        learnings = list(self._learnings.get(persona_id, []))

        package = ContextPackage(
            persona_id=persona_id,
            task_type=task_type,
            snapshots=snapshots,
            active_learnings=learnings,
        )
        logger.debug(
            "[PersonaMemoryLayer] Assembled context for %s: %d snapshots, %d learnings",
            persona_id, len(snapshots), len(learnings),
        )
        return package

    def health_check(self) -> dict:
        """Return health status."""
        return {
            "component": "PersonaMemoryLayer",
            "status": "healthy",
            "metrics": {
                "stored_personas": len(self._store),
                "total_snapshots": sum(len(v) for v in self._snapshots.values()),
                "total_learnings": sum(len(v) for v in self._learnings.values()),
            },
        }
