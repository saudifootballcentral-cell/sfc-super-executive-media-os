"""Tests for RealTimeMonitoringCenter."""
from __future__ import annotations

import pytest

from sfc.events.bus import get_event_bus
from sfc.war_rooms.operations.monitoring.models import (
    AlertSeverity,
    HealthReport,
    MonitoringAlert,
    MonitoringDomain,
    TrendReport,
)
from sfc.war_rooms.operations.monitoring.service import RealTimeMonitoringCenter


class TestRealTimeMonitoringCenter:
    def setup_method(self) -> None:
        get_event_bus().reset()
        self.service = RealTimeMonitoringCenter()

    async def test_check_domain_returns_score(self) -> None:
        score = await self.service.check_domain(MonitoringDomain.AGENTS)
        assert 0.0 <= score <= 100.0

    async def test_scan_all_domains_returns_health_report(self) -> None:
        report = await self.service.scan_all_domains()
        assert isinstance(report, HealthReport)
        assert report.report_id
        assert 0.0 <= report.overall_health <= 100.0
        assert len(report.domain_health) == len(list(MonitoringDomain))

    async def test_scan_all_domains_healthy_no_alerts(self) -> None:
        # Default domain health is 90 — above 70 threshold
        report = await self.service.scan_all_domains()
        assert report.active_alerts == []

    async def test_raise_alert_creates_alert(self) -> None:
        alert = await self.service.raise_alert(
            domain=MonitoringDomain.PLATFORMS,
            severity=AlertSeverity.HIGH,
            title="Platform degraded",
            description="Response time elevated",
            metric_name="response_time_ms",
            metric_value=2500.0,
            threshold=1000.0,
        )
        assert isinstance(alert, MonitoringAlert)
        assert alert.domain == MonitoringDomain.PLATFORMS
        assert not alert.resolved

    async def test_raise_alert_publishes_event(self) -> None:
        await self.service.raise_alert(
            domain=MonitoringDomain.REVENUE,
            severity=AlertSeverity.CRITICAL,
            title="Revenue drop",
            description="Revenue fell below threshold",
            metric_name="revenue_today",
            metric_value=1000.0,
            threshold=5000.0,
        )
        history = get_event_bus().get_history("monitoring_alert_raised")
        assert len(history) >= 1

    async def test_get_active_alerts_filters_resolved(self) -> None:
        alert = await self.service.raise_alert(
            domain=MonitoringDomain.AGENTS,
            severity=AlertSeverity.LOW,
            title="Minor issue",
            description="Minor",
            metric_name="latency",
            metric_value=200.0,
            threshold=100.0,
        )
        alert.resolved = True
        active = self.service.get_active_alerts()
        assert alert.alert_id not in [a.alert_id for a in active]

    async def test_get_trend_report(self) -> None:
        report = await self.service.get_trend_report()
        assert isinstance(report, TrendReport)
        assert len(report.trending_topics) > 0

    async def test_health_check(self) -> None:
        hc = self.service.health_check()
        assert hc["status"] == "healthy"
        assert hc["component"] == "real_time_monitoring_center"
