"""Tests for OperationalDashboardLayer."""
from __future__ import annotations

import pytest

from sfc.events.bus import get_event_bus
from sfc.war_rooms.operations.dashboards.models import Dashboard, DashboardType
from sfc.war_rooms.operations.dashboards.service import OperationalDashboardLayer


class TestOperationalDashboardLayer:
    def setup_method(self) -> None:
        get_event_bus().reset()
        self.service = OperationalDashboardLayer()

    async def test_build_executive_dashboard(self) -> None:
        dashboard = await self.service.build_executive_dashboard()
        assert isinstance(dashboard, Dashboard)
        assert dashboard.dashboard_type == DashboardType.EXECUTIVE
        widget_ids = [w.widget_id for w in dashboard.widgets]
        assert "system_health" in widget_ids
        assert "active_alerts" in widget_ids

    async def test_build_operations_dashboard(self) -> None:
        dashboard = await self.service.build_operations_dashboard()
        assert dashboard.dashboard_type == DashboardType.OPERATIONS
        widget_ids = [w.widget_id for w in dashboard.widgets]
        assert "agent_health" in widget_ids
        assert "error_rate" in widget_ids

    async def test_build_war_room_dashboard(self) -> None:
        dashboard = await self.service.build_war_room_dashboard("WR-TEST-001")
        assert dashboard.dashboard_type == DashboardType.WAR_ROOM
        assert "WR-TEST-001" in dashboard.title

    async def test_build_war_room_dashboard_no_id(self) -> None:
        dashboard = await self.service.build_war_room_dashboard()
        assert dashboard.dashboard_type == DashboardType.WAR_ROOM

    async def test_build_dispatcher_executive(self) -> None:
        dashboard = await self.service.build(DashboardType.EXECUTIVE)
        assert dashboard.dashboard_type == DashboardType.EXECUTIVE

    async def test_build_dispatcher_operations(self) -> None:
        dashboard = await self.service.build(DashboardType.OPERATIONS)
        assert dashboard.dashboard_type == DashboardType.OPERATIONS

    async def test_build_dispatcher_generic_types(self) -> None:
        for dt in [DashboardType.ANALYTICS, DashboardType.REVENUE, DashboardType.MONITORING]:
            dashboard = await self.service.build(dt)
            assert dashboard.dashboard_type == dt
            assert len(dashboard.widgets) > 0

    async def test_refresh_returns_updated_dashboard(self) -> None:
        original = await self.service.build_executive_dashboard()
        refreshed = await self.service.refresh(original.dashboard_id)
        assert refreshed.dashboard_id == original.dashboard_id
        assert refreshed.dashboard_type == DashboardType.EXECUTIVE

    async def test_refresh_publishes_event(self) -> None:
        dashboard = await self.service.build_executive_dashboard()
        get_event_bus().reset()
        await self.service.refresh(dashboard.dashboard_id)
        history = get_event_bus().get_history("dashboard_updated")
        assert len(history) == 1
        assert history[0].payload["dashboard_id"] == dashboard.dashboard_id

    async def test_refresh_nonexistent_raises(self) -> None:
        with pytest.raises(ValueError, match="Dashboard not found"):
            await self.service.refresh("nonexistent-dashboard-id")

    async def test_health_check(self) -> None:
        hc = self.service.health_check()
        assert hc["status"] == "healthy"
        assert hc["component"] == "operational_dashboard_layer"
