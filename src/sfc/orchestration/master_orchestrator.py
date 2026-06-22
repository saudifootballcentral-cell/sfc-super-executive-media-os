"""MasterOrchestrator — single entry point for all orchestrated workflow runs."""

from __future__ import annotations

from typing import Any

from sfc.orchestration.approval_gate import ApprovalGate
from sfc.orchestration.execution_plan import ExecutionPlan
from sfc.orchestration.graph_bridge import GraphBridge
from sfc.orchestration.master_state import MasterState, RunStatus, WorkflowType
from sfc.orchestration.persistence import InMemoryPersistence, PersistenceProvider
from sfc.orchestration.run_context import RunContext
from sfc.orchestration.status import OrchestrationStatus
from sfc.orchestration.workflow_runner import WorkflowRunner


class MasterOrchestrator:
    """Single operator-facing facade for launching and managing SFC workflows.

    Usage:
        orchestrator = MasterOrchestrator()

        # Dry run (default — safe, no live publishing)
        result = await orchestrator.run(
            task_type="transfer_news",
            task_payload={"headline": "Neymar joins Al Hilal"},
        )

        # Full live run (requires operator approval + LIVE_PUBLISHING_ENABLED=true)
        result = await orchestrator.run(
            task_type="transfer_news",
            task_payload={"headline": "Neymar joins Al Hilal"},
            workflow_type=WorkflowType.FULL_PIPELINE,
            dry_run=False,
        )

        # Social intelligence only
        result = await orchestrator.run(
            workflow_type=WorkflowType.SOCIAL_INTELLIGENCE_ONLY,
        )
    """

    def __init__(
        self,
        persistence: PersistenceProvider | None = None,
        bridge: GraphBridge | None = None,
    ) -> None:
        self._persistence = persistence or InMemoryPersistence()
        self._bridge = bridge or GraphBridge()
        self._runner = WorkflowRunner(bridge=self._bridge)
        self._gate = ApprovalGate()
        self._status = OrchestrationStatus()

    # ------------------------------------------------------------------
    # Primary API
    # ------------------------------------------------------------------

    async def run(
        self,
        task_type: str = "content_pipeline",
        task_payload: dict[str, Any] | None = None,
        workflow_type: WorkflowType = WorkflowType.DRY_RUN,
        dry_run: bool = True,
        initiator: str = "api",
        source: str = "api",
    ) -> MasterState:
        """Launch a new workflow run and execute it to completion (or pause).

        Returns the final MasterState for inspection.
        """
        state = MasterState(
            task_type=task_type,
            task_payload=task_payload or {},
            workflow_type=workflow_type,
            dry_run=dry_run,
            initiator=initiator,
            source=source,
        )
        plan = ExecutionPlan(workflow_type=workflow_type, dry_run=dry_run)
        ctx = RunContext(state=state, plan=plan, persistence=self._persistence)

        self._status.register(state)
        try:
            await self._runner.run(ctx)
        finally:
            self._status.complete(state)

        return state

    async def resume(self, run_id: str) -> MasterState | None:
        """Reload a persisted run and attempt to continue from last checkpoint."""
        state = await self._persistence.load(run_id)
        if state is None:
            return None
        if state.status in (RunStatus.COMPLETED, RunStatus.ABORTED):
            return state

        plan = ExecutionPlan(workflow_type=state.workflow_type, dry_run=state.dry_run)
        ctx = RunContext(state=state, plan=plan, persistence=self._persistence)

        self._status.register(state)
        try:
            await self._runner.run(ctx)
        finally:
            self._status.complete(state)

        return state

    def grant_operator_approval(
        self,
        run_id: str,
        granted_by: str = "operator",
        reason: str = "",
    ) -> bool:
        """Grant operator approval for a paused run.

        Must be followed by a call to resume(run_id) to continue publishing.
        Returns True if the run was found and updated, False otherwise.
        """
        state = self._status.get(run_id)
        if state is None:
            return False
        self._gate.grant_operator_approval(state, granted_by=granted_by, reason=reason)
        return True

    def deny_operator_approval(
        self,
        run_id: str,
        denied_by: str = "operator",
        reason: str = "",
    ) -> bool:
        state = self._status.get(run_id)
        if state is None:
            return False
        self._gate.deny_operator_approval(state, denied_by=denied_by, reason=reason)
        return True

    # ------------------------------------------------------------------
    # Convenience wrappers
    # ------------------------------------------------------------------

    async def run_social_intelligence(
        self, task_payload: dict[str, Any] | None = None
    ) -> MasterState:
        return await self.run(
            task_type="social_scan",
            task_payload=task_payload,
            workflow_type=WorkflowType.SOCIAL_INTELLIGENCE_ONLY,
            dry_run=True,
        )

    async def run_dry(
        self,
        task_type: str = "content_pipeline",
        task_payload: dict[str, Any] | None = None,
    ) -> MasterState:
        return await self.run(
            task_type=task_type,
            task_payload=task_payload,
            workflow_type=WorkflowType.DRY_RUN,
            dry_run=True,
        )

    # ------------------------------------------------------------------
    # Status & inspection
    # ------------------------------------------------------------------

    def status(self) -> dict[str, Any]:
        return self._status.health()

    def active_runs(self) -> list[dict[str, Any]]:
        return [s.to_dict() for s in self._status.active_runs()]

    async def list_runs(self, limit: int = 20) -> list[dict[str, Any]]:
        return await self._persistence.list_runs(limit=limit)

    async def get_run(self, run_id: str) -> MasterState | None:
        # Check active first
        state = self._status.get(run_id)
        if state:
            return state
        return await self._persistence.load(run_id)
