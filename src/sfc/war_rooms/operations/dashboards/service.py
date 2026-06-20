"""Operational Dashboard Layer — service implementation."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sfc.events.bus import get_event_bus
from sfc.war_rooms.operations.dashboards.models import (
    Dashboard,
    DashboardType,
    WidgetData,
)
from sfc.war_rooms.shared.events import DashboardUpdated

logger = logging.getLogger("sfc.war_rooms.operations.dashboards")


def _widget(widget_id: str, title: str, value: Any, unit: str = "", status: str = "ok") -> WidgetData:
    return WidgetData(
        widget_id=widget_id,
        title=title,
        value=value,
        unit=unit,
        status=status,
        updated_at=datetime.utcnow(),
    )


class OperationalDashboardLayer:
    """Builds and manages operational dashboards across the platform."""

    def __init__(self) -> None:
        self._dashboards: dict[str, Dashboard] = {}

    async def build_executive_dashboard(self) -> Dashboard:
        """Build the executive-level dashboard."""
        widgets = [
            _widget("system_health", "System Health", 98.0, "%", "ok"),
            _widget("war_room_status", "Active War Rooms", 0, "rooms", "ok"),
            _widget("active_alerts", "Active Alerts", 0, "alerts", "ok"),
            _widget("priority_queue", "Priority Queue Depth", 0, "items", "ok"),
            _widget("revenue_status", "Revenue Status", "on_track", "", "ok"),
            _widget("publishing_status", "Publishing Status", "operational", "", "ok"),
        ]
        dashboard = Dashboard(
            dashboard_type=DashboardType.EXECUTIVE,
            title="SFC Executive Dashboard",
            widgets=widgets,
            generated_at=datetime.utcnow(),
            refresh_interval_seconds=30,
        )
        self._dashboards[dashboard.dashboard_id] = dashboard
        return dashboard

    async def build_operations_dashboard(self) -> Dashboard:
        """Build the operations-level dashboard."""
        widgets = [
            _widget("workflow_status", "Active Workflows", 0, "workflows", "ok"),
            _widget("agent_health", "Agent Health", 100.0, "%", "ok"),
            _widget("tool_health", "Tool Health", 100.0, "%", "ok"),
            _widget("platform_health", "Platform Health", 100.0, "%", "ok"),
            _widget("queue_depth", "Queue Depth", 0, "items", "ok"),
            _widget("error_rate", "Error Rate", 0.0, "%", "ok"),
        ]
        dashboard = Dashboard(
            dashboard_type=DashboardType.OPERATIONS,
            title="SFC Operations Dashboard",
            widgets=widgets,
            generated_at=datetime.utcnow(),
            refresh_interval_seconds=15,
        )
        self._dashboards[dashboard.dashboard_id] = dashboard
        return dashboard

    async def build_war_room_dashboard(self, war_room_id: str | None = None) -> Dashboard:
        """Build a war room status dashboard."""
        widgets = [
            _widget("active_war_rooms", "Active War Rooms", 0, "rooms", "ok"),
            _widget("war_room_health", "War Room Health", 100.0, "%", "ok"),
            _widget("resource_utilization", "Resource Utilization", 0.0, "%", "ok"),
            _widget("events_processed", "Events Processed", 0, "events", "ok"),
            _widget("escalations", "Escalations", 0, "open", "ok"),
        ]
        title = f"War Room Dashboard — {war_room_id}" if war_room_id else "War Room Dashboard"
        dashboard = Dashboard(
            dashboard_type=DashboardType.WAR_ROOM,
            title=title,
            widgets=widgets,
            generated_at=datetime.utcnow(),
            refresh_interval_seconds=10,
        )
        self._dashboards[dashboard.dashboard_id] = dashboard
        return dashboard

    async def build(self, dashboard_type: DashboardType) -> Dashboard:
        """Dispatcher — build the dashboard matching the given type."""
        if dashboard_type == DashboardType.EXECUTIVE:
            return await self.build_executive_dashboard()
        if dashboard_type == DashboardType.OPERATIONS:
            return await self.build_operations_dashboard()
        if dashboard_type == DashboardType.WAR_ROOM:
            return await self.build_war_room_dashboard()

        # Generic fallback for remaining types
        widgets = [
            _widget(f"{dashboard_type.value}_status", f"{dashboard_type.value.capitalize()} Status", "operational", "", "ok"),
            _widget(f"{dashboard_type.value}_health", "Health", 100.0, "%", "ok"),
        ]
        dashboard = Dashboard(
            dashboard_type=dashboard_type,
            title=f"SFC {dashboard_type.value.capitalize()} Dashboard",
            widgets=widgets,
            generated_at=datetime.utcnow(),
        )
        self._dashboards[dashboard.dashboard_id] = dashboard
        return dashboard

    async def refresh(self, dashboard_id: str) -> Dashboard:
        """Rebuild a dashboard and publish a DashboardUpdated event."""
        existing = self._dashboards.get(dashboard_id)
        if existing is None:
            raise ValueError(f"Dashboard not found: {dashboard_id}")

        refreshed = await self.build(existing.dashboard_type)
        # Preserve the same ID for stable references
        self._dashboards.pop(refreshed.dashboard_id, None)
        refreshed = Dashboard(
            dashboard_id=dashboard_id,
            dashboard_type=refreshed.dashboard_type,
            title=refreshed.title,
            widgets=refreshed.widgets,
            generated_at=datetime.utcnow(),
            refresh_interval_seconds=refreshed.refresh_interval_seconds,
        )
        self._dashboards[dashboard_id] = refreshed

        get_event_bus().publish(
            DashboardUpdated(
                division="operations",
                run_id=dashboard_id,
                payload={
                    "dashboard_id": dashboard_id,
                    "dashboard_type": existing.dashboard_type.value,
                    "widget_count": len(refreshed.widgets),
                },
            )
        )
        logger.info("[Dashboard] Refreshed: %s (%s)", dashboard_id, existing.dashboard_type.value)
        return refreshed

    def health_check(self) -> dict[str, Any]:
        return {
            "component": "operational_dashboard_layer",
            "status": "healthy",
            "dashboards_cached": len(self._dashboards),
        }
