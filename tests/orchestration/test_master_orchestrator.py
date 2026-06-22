"""Tests for MasterOrchestrator — Package 10D.

All tests use a mock GraphBridge to avoid invoking real LangGraph graphs.
"""

from __future__ import annotations

import pytest

from sfc.orchestration.master_orchestrator import MasterOrchestrator
from sfc.orchestration.master_state import RunStatus, WorkflowType
from sfc.orchestration.persistence import InMemoryPersistence


class MockBridge:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def execute(self, graph_name, run_id, task_type, task_payload, prior_state=None):
        self.calls.append(graph_name)
        return {
            "run_id": run_id,
            "task_type": task_type,
            "task_payload": task_payload,
            "pipeline_stage": "completed",
            "governance_reviews": [{"approved": True}],
            "approved_content": [{"id": "c1"}],
            "rejected_content": [],
            "warnings": [],
            "errors": [],
        }


def _make_orchestrator():
    bridge = MockBridge()
    persistence = InMemoryPersistence()
    orch = MasterOrchestrator(persistence=persistence, bridge=bridge)
    return orch, bridge, persistence


class TestMasterOrchestratorRun:
    @pytest.mark.asyncio
    async def test_run_social_only_returns_completed_state(self):
        orch, _, _ = _make_orchestrator()
        state = await orch.run_social_intelligence()
        assert state.status == RunStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_run_dry_returns_completed_state(self):
        orch, _, _ = _make_orchestrator()
        state = await orch.run_dry()
        assert state.status == RunStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_run_returns_master_state(self):
        orch, _, _ = _make_orchestrator()
        from sfc.orchestration.master_state import MasterState
        state = await orch.run_social_intelligence()
        assert isinstance(state, MasterState)

    @pytest.mark.asyncio
    async def test_run_id_populated(self):
        orch, _, _ = _make_orchestrator()
        state = await orch.run_social_intelligence()
        assert len(state.run_id) > 0

    @pytest.mark.asyncio
    async def test_dry_run_flag_preserved(self):
        orch, _, _ = _make_orchestrator()
        state = await orch.run_dry()
        assert state.dry_run is True

    @pytest.mark.asyncio
    async def test_workflow_type_preserved(self):
        orch, _, _ = _make_orchestrator()
        state = await orch.run(
            workflow_type=WorkflowType.SOCIAL_INTELLIGENCE_ONLY,
            dry_run=True,
        )
        assert state.workflow_type == WorkflowType.SOCIAL_INTELLIGENCE_ONLY


class TestMasterOrchestratorStatus:
    @pytest.mark.asyncio
    async def test_status_returns_dict(self):
        orch, _, _ = _make_orchestrator()
        result = orch.status()
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_completed_runs_persist(self):
        orch, _, persistence = _make_orchestrator()
        state = await orch.run_social_intelligence()
        loaded = await persistence.load(state.run_id)
        assert loaded is not None

    @pytest.mark.asyncio
    async def test_list_runs_returns_list(self):
        orch, _, _ = _make_orchestrator()
        await orch.run_social_intelligence()
        runs = await orch.list_runs()
        assert isinstance(runs, list)
        assert len(runs) >= 1

    @pytest.mark.asyncio
    async def test_get_run_returns_completed_state(self):
        orch, _, _ = _make_orchestrator()
        state = await orch.run_social_intelligence()
        loaded = await orch.get_run(state.run_id)
        assert loaded is not None
        assert loaded.run_id == state.run_id


class TestOperatorApproval:
    def test_grant_approval_for_active_run(self):
        orch, _, _ = _make_orchestrator()
        # Manually register a state in active runs
        from sfc.orchestration.master_state import MasterState
        state = MasterState()
        orch._status.register(state)
        result = orch.grant_operator_approval(state.run_id, granted_by="ceo")
        assert result is True
        assert state.approval.operator_approved is True

    def test_grant_approval_unknown_run_returns_false(self):
        orch, _, _ = _make_orchestrator()
        result = orch.grant_operator_approval("nonexistent-run-id")
        assert result is False

    def test_deny_approval_for_active_run(self):
        orch, _, _ = _make_orchestrator()
        from sfc.orchestration.master_state import MasterState
        state = MasterState()
        orch._status.register(state)
        result = orch.deny_operator_approval(state.run_id, denied_by="compliance")
        assert result is True
        assert state.status == RunStatus.ABORTED


class TestNoBypass:
    @pytest.mark.asyncio
    async def test_publishing_skipped_without_live_env(self, monkeypatch):
        """Verify publishing stage is never run when LIVE_PUBLISHING_ENABLED is not set."""
        monkeypatch.delenv("LIVE_PUBLISHING_ENABLED", raising=False)
        orch, bridge, _ = _make_orchestrator()
        state = await orch.run(
            workflow_type=WorkflowType.DRY_RUN,
            dry_run=True,
        )
        assert "publishing_connectors_graph" not in bridge.calls

    @pytest.mark.asyncio
    async def test_governance_gate_runs_in_every_full_pipeline(self):
        orch, bridge, _ = _make_orchestrator()
        state = await orch.run(
            workflow_type=WorkflowType.DRY_RUN,
            dry_run=True,
        )
        assert "governance_gate" in state.completed_stages or "governance_gate" in state.stages
