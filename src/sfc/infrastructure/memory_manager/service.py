"""Memory Manager — unified facade over the 5-layer memory system."""

from __future__ import annotations

import logging
import threading
from datetime import datetime
from typing import Any

from sfc.core.models import Division
from sfc.memory.global_memory import GlobalMemory
from sfc.memory.division_memory import DivisionMemory
from sfc.memory.episodic_memory import EpisodicMemory
from sfc.memory.working_memory import WorkingMemory
from sfc.infrastructure.shared.types import ComponentHealth, HealthStatus

logger = logging.getLogger("sfc.infrastructure.memory_manager")


class MemoryManagerService:
    """Centralised memory access — all memory writes from divisions go through here.

    Memory hierarchy:
    - Working: task-scoped, auto-expire 24h
    - Division: per-division, 30-day retention
    - Global: permanent, cross-division
    - Episodic: lessons, permanent
    - Persona: 4 personas, permanent (managed by PersonaMemory)
    """

    def __init__(self) -> None:
        self._global = GlobalMemory()
        self._episodic = EpisodicMemory()
        self._working = WorkingMemory()
        self._division_stores: dict[str, DivisionMemory] = {}
        self._archive: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()

        # Pre-create division memories for known divisions
        for division in Division:
            self._division_stores[division.value] = DivisionMemory(division)

    # ------------------------------------------------------------------
    # Division Memory
    # ------------------------------------------------------------------

    def get_division_memory(self, division: str) -> DivisionMemory:
        """Return (or create) the DivisionMemory for a given division."""
        with self._lock:
            if division not in self._division_stores:
                # Try to match a Division enum value
                try:
                    div_enum = Division(division)
                    self._division_stores[division] = DivisionMemory(div_enum)
                except ValueError:
                    # Create a pseudo-division memory using a valid Division enum
                    self._division_stores[division] = DivisionMemory(Division.AGENTOPS)
            return self._division_stores[division]

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def store(
        self,
        namespace: str,
        key: str,
        value: Any,
        division: str | None = None,
    ) -> None:
        """Store a value in the appropriate memory layer."""
        if division is not None:
            div_mem = self.get_division_memory(division)
            div_mem.set(f"{namespace}:{key}", value)
        else:
            self._global.set(namespace, key, value)
        logger.debug("[MemoryManager] STORE %s/%s div=%s", namespace, key, division)

    async def retrieve(
        self,
        namespace: str,
        key: str,
        division: str | None = None,
    ) -> Any:
        """Retrieve from memory."""
        if division is not None:
            div_mem = self.get_division_memory(division)
            return div_mem.get(f"{namespace}:{key}")
        return self._global.get(namespace, key)

    async def search(
        self,
        query: str,
        namespace: str | None = None,
    ) -> list[dict[str, Any]]:
        """Simple keyword search across namespaces."""
        results: list[dict[str, Any]] = []
        query_lower = query.lower()

        # Search global memory
        snapshot = self._global.snapshot()
        for ns, ns_data in snapshot.items():
            if namespace and ns != namespace:
                continue
            for key, value in ns_data.items():
                if query_lower in key.lower() or (
                    isinstance(value, str) and query_lower in value.lower()
                ) or (
                    isinstance(value, dict) and any(
                        query_lower in str(v).lower() for v in value.values()
                    )
                ):
                    results.append({
                        "namespace": ns,
                        "key": key,
                        "value": value,
                        "source": "global",
                    })

        # Search division memories
        with self._lock:
            for div_name, div_mem in self._division_stores.items():
                div_snapshot = div_mem.snapshot()
                for key, value in div_snapshot.items():
                    if namespace and not key.startswith(f"{namespace}:"):
                        continue
                    if query_lower in key.lower() or (
                        isinstance(value, str) and query_lower in value.lower()
                    ):
                        results.append({
                            "namespace": namespace or "division",
                            "key": key,
                            "value": value,
                            "source": f"division:{div_name}",
                            "division": div_name,
                        })

        return results

    async def update(
        self,
        namespace: str,
        key: str,
        value: Any,
        division: str | None = None,
    ) -> None:
        """Update existing memory entry (same as store)."""
        await self.store(namespace, key, value, division)

    async def archive(self, namespace: str, key: str) -> None:
        """Move entry to archive (cold storage)."""
        value = self._global.get(namespace, key)
        if value is not None:
            with self._lock:
                if namespace not in self._archive:
                    self._archive[namespace] = {}
                self._archive[namespace][key] = {
                    "value": value,
                    "archived_at": datetime.utcnow().isoformat(),
                }
            self._global.delete(namespace, key)
            logger.info("[MemoryManager] ARCHIVE %s/%s", namespace, key)

    async def expire(self, namespace: str, key: str) -> None:
        """Delete expired entry."""
        self._global.delete(namespace, key)
        logger.debug("[MemoryManager] EXPIRE %s/%s", namespace, key)

    async def record_episode(
        self,
        run_id: str,
        event: str,
        decision: str,
        result: str,
        lesson: str,
        division: str | None = None,
    ) -> None:
        """Record an episodic memory entry from any division."""
        try:
            div_enum = Division(division) if division else None
        except ValueError:
            div_enum = None

        self._episodic.record(
            run_id=run_id,
            event=event,
            decision=decision,
            result=result,
            lesson=lesson,
            division=div_enum,
        )
        logger.info("[MemoryManager] Episode recorded for run %s", run_id)

    async def summarize(self, namespace: str, max_items: int = 10) -> str:
        """Summarise stored items in a namespace."""
        all_data = self._global.get_all(namespace)
        items = list(all_data.items())[:max_items]

        if not items:
            return f"Namespace '{namespace}' is empty."

        lines = [f"Summary of '{namespace}' ({len(all_data)} total entries, showing {len(items)}):"]
        for key, value in items:
            if isinstance(value, dict):
                summary = ", ".join(f"{k}={v}" for k, v in list(value.items())[:3])
            else:
                summary = str(value)[:100]
            lines.append(f"  - {key}: {summary}")

        return "\n".join(lines)

    def health_check(self) -> ComponentHealth:
        """Return health status of the memory manager."""
        try:
            total_entries = self._global.total_entries()
            episode_count = self._episodic.total_count
            division_count = len(self._division_stores)

            return ComponentHealth(
                component="memory_manager",
                status=HealthStatus.HEALTHY,
                last_check=datetime.utcnow(),
                metrics={
                    "global_entries": total_entries,
                    "episode_count": episode_count,
                    "division_stores": division_count,
                    "archive_entries": sum(len(v) for v in self._archive.values()),
                },
            )
        except Exception as exc:  # noqa: BLE001
            return ComponentHealth(
                component="memory_manager",
                status=HealthStatus.UNHEALTHY,
                last_check=datetime.utcnow(),
                metrics={},
                errors=[str(exc)],
            )
