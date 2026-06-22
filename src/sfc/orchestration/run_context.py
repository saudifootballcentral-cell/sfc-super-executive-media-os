"""RunContext — per-run dependency container passed to every stage executor."""

from __future__ import annotations

from typing import Any

from sfc.orchestration.approval_gate import ApprovalGate
from sfc.orchestration.audit_trail import AuditTrail
from sfc.orchestration.execution_plan import ExecutionPlan
from sfc.orchestration.master_state import MasterState
from sfc.orchestration.persistence import InMemoryPersistence, PersistenceProvider


class RunContext:
    """Container that holds all per-run dependencies for the WorkflowRunner."""

    def __init__(
        self,
        state: MasterState,
        plan: ExecutionPlan,
        persistence: PersistenceProvider | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        self.state = state
        self.plan = plan
        self.audit = AuditTrail(run_id=state.run_id)
        self.gate = ApprovalGate()
        self.persistence: PersistenceProvider = persistence or InMemoryPersistence()
        self.extra: dict[str, Any] = extra or {}
        self._graph_cache: dict[str, Any] = {}

    def cache_graph(self, name: str, graph: Any) -> None:
        self._graph_cache[name] = graph

    def get_graph(self, name: str) -> Any | None:
        return self._graph_cache.get(name)

    async def checkpoint(self) -> None:
        """Persist current state snapshot."""
        await self.persistence.save(self.state)

    @property
    def run_id(self) -> str:
        return self.state.run_id

    @property
    def dry_run(self) -> bool:
        return self.state.dry_run
