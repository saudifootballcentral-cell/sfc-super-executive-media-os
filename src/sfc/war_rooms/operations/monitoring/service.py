"""Real-Time Monitoring Center — service implementation."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sfc.events.bus import get_event_bus
from sfc.war_rooms.operations.monitoring.models import (
    AlertSeverity,
    HealthReport,
    MonitoringAlert,
    MonitoringDomain,
    TrendReport,
)
from sfc.war_rooms.shared.events import MonitoringAlertRaised

logger = logging.getLogger("sfc.war_rooms.operations.monitoring")

_HEALTH_THRESHOLD = 70.0
_DEFAULT_DOMAIN_HEALTH = 90.0


class RealTimeMonitoringCenter:
    """Central monitoring hub covering all operational domains."""

    def __init__(self) -> None:
        self._alerts: dict[str, MonitoringAlert] = {}
        self._domain_baselines: dict[str, float] = {
            d.value: _DEFAULT_DOMAIN_HEALTH for d in MonitoringDomain
        }

    async def check_domain(self, domain: MonitoringDomain) -> float:
        """Return health score (0-100) for a given domain."""
        return self._domain_baselines.get(domain.value, _DEFAULT_DOMAIN_HEALTH)

    async def scan_all_domains(self) -> HealthReport:
        """Scan all monitoring domains; raise alerts for unhealthy ones."""
        domain_health: dict[str, float] = {}
        active_alerts: list[MonitoringAlert] = []
        warnings: list[str] = []
        recommendations: list[str] = []

        for domain in MonitoringDomain:
            score = await self.check_domain(domain)
            domain_health[domain.value] = score

            if score < _HEALTH_THRESHOLD:
                alert = await self.raise_alert(
                    domain=domain,
                    severity=AlertSeverity.HIGH,
                    title=f"{domain.value.capitalize()} health degraded",
                    description=f"Health score {score:.1f} is below threshold {_HEALTH_THRESHOLD}",
                    metric_name="health_score",
                    metric_value=score,
                    threshold=_HEALTH_THRESHOLD,
                )
                active_alerts.append(alert)
                warnings.append(f"{domain.value}: health={score:.1f}")
                recommendations.append(f"Investigate {domain.value} degradation immediately")

        overall = sum(domain_health.values()) / len(domain_health) if domain_health else 100.0
        report = HealthReport(
            generated_at=datetime.utcnow(),
            overall_health=round(overall, 2),
            domain_health=domain_health,
            active_alerts=active_alerts,
            warnings=warnings,
            recommendations=recommendations,
        )
        logger.info("[Monitoring] Health scan complete: overall=%.1f", overall)
        return report

    async def get_trend_report(self) -> TrendReport:
        """Return a current trend report."""
        return TrendReport(
            generated_at=datetime.utcnow(),
            trending_topics=["Saudi Pro League", "Al-Hilal", "Al-Nassr", "World Cup 2034"],
            sentiment_trend="positive",
            audience_growth_pct=3.2,
            engagement_rate=6.8,
            revenue_trend="growing",
        )

    async def raise_alert(
        self,
        domain: MonitoringDomain,
        severity: AlertSeverity,
        title: str,
        description: str,
        metric_name: str,
        metric_value: float,
        threshold: float,
    ) -> MonitoringAlert:
        """Create and publish a monitoring alert."""
        alert = MonitoringAlert(
            domain=domain,
            severity=severity,
            title=title,
            description=description,
            metric_name=metric_name,
            metric_value=metric_value,
            threshold=threshold,
            raised_at=datetime.utcnow(),
        )
        self._alerts[alert.alert_id] = alert

        get_event_bus().publish(
            MonitoringAlertRaised(
                division="operations",
                run_id=alert.alert_id,
                payload={
                    "alert_id": alert.alert_id,
                    "domain": domain.value,
                    "severity": severity.value,
                    "title": title,
                    "metric_name": metric_name,
                    "metric_value": metric_value,
                    "threshold": threshold,
                },
            )
        )
        logger.warning("[Monitoring] Alert raised: %s [%s] — %s", title, severity.value, domain.value)
        return alert

    def get_active_alerts(self) -> list[MonitoringAlert]:
        """Return all unresolved alerts."""
        return [a for a in self._alerts.values() if not a.resolved]

    def health_check(self) -> dict[str, Any]:
        return {
            "component": "real_time_monitoring_center",
            "status": "healthy",
            "total_alerts": len(self._alerts),
            "active_alerts": len(self.get_active_alerts()),
            "domains_monitored": len(list(MonitoringDomain)),
        }
