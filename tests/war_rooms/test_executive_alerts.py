"""Tests for ExecutiveAlertSystem."""
from __future__ import annotations

import pytest

from sfc.events.bus import get_event_bus
from sfc.war_rooms.operations.executive_alerts.models import (
    AlertCategory,
    AlertSeverity,
    ExecutiveAlert,
    ExecutiveSummary,
)
from sfc.war_rooms.operations.executive_alerts.service import ExecutiveAlertSystem


class TestExecutiveAlertSystem:
    def setup_method(self) -> None:
        get_event_bus().reset()
        self.service = ExecutiveAlertSystem()

    async def test_raise_alert_returns_alert(self) -> None:
        alert = await self.service.raise_alert(
            category=AlertCategory.BREAKING_NEWS,
            severity=AlertSeverity.HIGH,
            title="Major match result",
            summary="Al-Hilal won the championship",
        )
        assert isinstance(alert, ExecutiveAlert)
        assert alert.title == "Major match result"
        assert not alert.acknowledged

    async def test_raise_alert_publishes_event(self) -> None:
        await self.service.raise_alert(
            category=AlertCategory.CRISIS,
            severity=AlertSeverity.CRITICAL,
            title="Crisis detected",
            summary="Reputational crisis emerging",
        )
        history = get_event_bus().get_history("executive_alert_triggered")
        assert len(history) == 1
        assert history[0].payload["severity"] == "critical"

    async def test_acknowledge_marks_acknowledged(self) -> None:
        alert = await self.service.raise_alert(
            category=AlertCategory.SYSTEM_FAILURE,
            severity=AlertSeverity.HIGH,
            title="Service down",
            summary="Platform failure",
        )
        acked = await self.service.acknowledge(alert.alert_id)
        assert acked.acknowledged is True
        assert acked.acknowledged_at is not None

    async def test_acknowledge_nonexistent_raises(self) -> None:
        with pytest.raises(ValueError, match="Alert not found"):
            await self.service.acknowledge("nonexistent-id")

    async def test_get_active_alerts_excludes_acknowledged(self) -> None:
        alert = await self.service.raise_alert(
            category=AlertCategory.BREAKING_NEWS,
            severity=AlertSeverity.MEDIUM,
            title="Story",
            summary="Story summary",
        )
        await self.service.acknowledge(alert.alert_id)
        active = self.service.get_active_alerts()
        assert alert.alert_id not in [a.alert_id for a in active]

    async def test_get_critical_alerts(self) -> None:
        await self.service.raise_alert(
            category=AlertCategory.CRISIS,
            severity=AlertSeverity.CRITICAL,
            title="Critical issue",
            summary="Very serious",
        )
        await self.service.raise_alert(
            category=AlertCategory.BREAKING_NEWS,
            severity=AlertSeverity.LOW,
            title="Minor update",
            summary="Minor",
        )
        critical = self.service.get_critical_alerts()
        assert len(critical) == 1
        assert critical[0].severity == AlertSeverity.CRITICAL

    async def test_generate_summary(self) -> None:
        await self.service.raise_alert(
            category=AlertCategory.REVENUE_OPPORTUNITY,
            severity=AlertSeverity.MEDIUM,
            title="Revenue opportunity",
            summary="New revenue channel identified",
        )
        summary = await self.service.generate_summary()
        assert isinstance(summary, ExecutiveSummary)
        assert summary.period == "session"
        assert summary.metrics["total_alerts"] == 1

    async def test_health_check(self) -> None:
        hc = self.service.health_check()
        assert hc["status"] == "healthy"
        assert hc["component"] == "executive_alert_system"
