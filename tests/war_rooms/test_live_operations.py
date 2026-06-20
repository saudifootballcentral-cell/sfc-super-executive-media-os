"""Tests for LiveOperationsCommand."""
from __future__ import annotations

import pytest

from sfc.events.bus import get_event_bus
from sfc.war_rooms.operations.live_operations.models import (
    OperationalStatus,
    OperationsAlert,
    OperationsSnapshot,
    WorkflowStatus,
)
from sfc.war_rooms.operations.live_operations.service import LiveOperationsCommand


class TestLiveOperationsCommand:
    def setup_method(self) -> None:
        get_event_bus().reset()
        self.service = LiveOperationsCommand()

    async def test_snapshot_returns_snapshot(self) -> None:
        snapshot = await self.service.snapshot()
        assert isinstance(snapshot, OperationsSnapshot)
        assert snapshot.snapshot_id
        assert snapshot.overall_status == OperationalStatus.HEALTHY

    async def test_snapshot_has_platform_health(self) -> None:
        snapshot = await self.service.snapshot()
        assert snapshot.platforms_healthy >= 0

    async def test_monitor_workflows_creates_stubs(self) -> None:
        wf_ids = ["wf-001", "wf-002"]
        result = await self.service.monitor_workflows(wf_ids)
        assert len(result) == 2
        assert all(isinstance(w, WorkflowStatus) for w in result)

    async def test_monitor_workflows_returns_existing(self) -> None:
        await self.service.monitor_workflows(["wf-abc"])
        result = await self.service.monitor_workflows(["wf-abc"])
        assert result[0].workflow_id == "wf-abc"

    async def test_get_platform_health_returns_all_healthy(self) -> None:
        health = await self.service.get_platform_health()
        assert len(health) > 0
        assert all(v == OperationalStatus.HEALTHY for v in health.values())

    async def test_trigger_recovery_resolves_alert(self) -> None:
        alert = OperationsAlert(severity="high", message="Platform down", source="monitor")
        recovery = await self.service.trigger_recovery(alert)
        assert "steps" in recovery
        assert alert.resolved is True

    async def test_report_returns_dict(self) -> None:
        report = await self.service.report()
        assert "snapshot" in report
        assert "platform_health" in report

    async def test_health_check(self) -> None:
        hc = self.service.health_check()
        assert hc["status"] == "healthy"
        assert hc["component"] == "live_operations_command"
