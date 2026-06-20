"""Executive Alert System — service implementation."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sfc.events.bus import get_event_bus
from sfc.war_rooms.operations.executive_alerts.models import (
    AlertCategory,
    AlertSeverity,
    ExecutiveAlert,
    ExecutiveSummary,
)
from sfc.war_rooms.shared.events import ExecutiveAlertTriggered

logger = logging.getLogger("sfc.war_rooms.operations.executive_alerts")


class ExecutiveAlertSystem:
    """Alert system for surfacing high-priority items to executive decision-makers."""

    def __init__(self) -> None:
        self._alerts: dict[str, ExecutiveAlert] = {}

    async def raise_alert(
        self,
        category: AlertCategory,
        severity: AlertSeverity,
        title: str,
        summary: str,
        action_required: bool = False,
        recommended_action: str = "",
        context: dict[str, Any] | None = None,
    ) -> ExecutiveAlert:
        """Create an executive alert and publish event."""
        context = context or {}
        alert = ExecutiveAlert(
            category=category,
            severity=severity,
            title=title,
            summary=summary,
            action_required=action_required,
            recommended_action=recommended_action,
            context=context,
            raised_at=datetime.utcnow(),
        )
        self._alerts[alert.alert_id] = alert

        get_event_bus().publish(
            ExecutiveAlertTriggered(
                division="operations",
                run_id=alert.alert_id,
                payload={
                    "alert_id": alert.alert_id,
                    "category": category.value,
                    "severity": severity.value,
                    "title": title,
                    "action_required": action_required,
                },
            )
        )
        logger.warning(
            "[ExecutiveAlert] %s [%s/%s]: %s",
            alert.alert_id,
            category.value,
            severity.value,
            title,
        )
        return alert

    async def acknowledge(self, alert_id: str) -> ExecutiveAlert:
        """Acknowledge an executive alert."""
        alert = self._alerts.get(alert_id)
        if alert is None:
            raise ValueError(f"Alert not found: {alert_id}")
        alert.acknowledged = True
        alert.acknowledged_at = datetime.utcnow()
        logger.info("[ExecutiveAlert] Acknowledged: %s", alert_id)
        return alert

    async def generate_summary(self, period: str = "session") -> ExecutiveSummary:
        """Synthesize all alerts into an executive summary."""
        all_alerts = list(self._alerts.values())
        critical_alerts = [a for a in all_alerts if a.severity == AlertSeverity.CRITICAL]
        action_required = [a for a in all_alerts if a.action_required]
        opportunities = [
            a for a in all_alerts
            if a.category in (AlertCategory.MAJOR_OPPORTUNITY, AlertCategory.REVENUE_OPPORTUNITY)
        ]
        risks = [
            a for a in all_alerts
            if a.category in (
                AlertCategory.CRISIS,
                AlertCategory.SECURITY_INCIDENT,
                AlertCategory.GOVERNANCE_FAILURE,
                AlertCategory.SYSTEM_FAILURE,
            )
        ]

        headline = (
            f"{len(critical_alerts)} critical alert(s) — "
            f"{len(action_required)} decision(s) required"
            if all_alerts
            else "No active executive alerts"
        )

        return ExecutiveSummary(
            period=period,
            headline=headline,
            key_points=[a.title for a in all_alerts[:5]],
            decisions_required=[a.recommended_action for a in action_required if a.recommended_action],
            opportunities=[a.title for a in opportunities],
            risks=[a.title for a in risks],
            metrics={
                "total_alerts": len(all_alerts),
                "critical": len(critical_alerts),
                "acknowledged": len([a for a in all_alerts if a.acknowledged]),
                "unacknowledged": len([a for a in all_alerts if not a.acknowledged]),
            },
            generated_at=datetime.utcnow(),
        )

    def get_active_alerts(self) -> list[ExecutiveAlert]:
        """Return all non-acknowledged alerts."""
        return [a for a in self._alerts.values() if not a.acknowledged]

    def get_critical_alerts(self) -> list[ExecutiveAlert]:
        """Return all CRITICAL severity alerts."""
        return [a for a in self._alerts.values() if a.severity == AlertSeverity.CRITICAL]

    def health_check(self) -> dict[str, Any]:
        return {
            "component": "executive_alert_system",
            "status": "healthy",
            "total_alerts": len(self._alerts),
            "active_alerts": len(self.get_active_alerts()),
            "critical_alerts": len(self.get_critical_alerts()),
        }
