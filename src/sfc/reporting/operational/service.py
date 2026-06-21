"""Operational Report Service — generates war room, platform, persona, and governance reports."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sfc.reporting.operational.models import OperationalReport, OperationalReportType

logger = logging.getLogger("sfc.reporting.operational.service")


class OperationalReportService:
    """Generates all operational report types."""

    def __init__(self) -> None:
        self._history: list[OperationalReport] = []

    async def generate_war_room_report(self, state: dict[str, Any]) -> OperationalReport:
        ws = state.get("war_room_state", {})
        activated = ws.get("activated", False)
        wrt = ws.get("war_room_type", "none")
        alerts = []
        if activated:
            alerts.append(f"War room activated: {wrt}")
        if ws.get("escalation_level") == "critical":
            alerts.append("CRITICAL escalation level detected")

        report = OperationalReport(
            report_type=OperationalReportType.WAR_ROOM,
            title="War Room Operational Report",
            summary=f"War room status: {'ACTIVE' if activated else 'INACTIVE'} ({wrt})",
            data=ws,
            metrics={
                "activated": float(activated),
                "escalation_numeric": 1.0 if ws.get("escalation_level") == "critical" else 0.0,
            },
            alerts=alerts,
            status="critical" if (activated and ws.get("escalation_level") == "critical") else (
                "warning" if activated else "ok"
            ),
        )
        self._store(report)
        return report

    async def generate_platform_report(self, state: dict[str, Any]) -> OperationalReport:
        analytics = state.get("analytics_report", {})
        publish_results = state.get("publish_results", {})
        platform_results = publish_results.get("platform_results", {})
        platforms_reached = analytics.get("platforms_reached", 0)

        metrics: dict[str, float] = {
            "platforms_reached": float(platforms_reached),
            "estimated_reach": float(analytics.get("estimated_reach", 0)),
            "engagement_rate": float(analytics.get("estimated_engagement_rate", 0)),
            "performance_score": float(analytics.get("performance_score", 0)),
        }
        alerts = []
        if platforms_reached == 0:
            alerts.append("No platforms reached — check publishing configuration")
        if analytics.get("performance_score", 100) < 50:
            alerts.append("Performance score below 50 — content strategy review needed")

        report = OperationalReport(
            report_type=OperationalReportType.PLATFORM,
            title="Platform Distribution Report",
            summary=(
                f"{platforms_reached} platform(s) reached with estimated "
                f"{int(analytics.get('estimated_reach', 0)):,} impressions"
            ),
            data={"platform_results": platform_results, "analytics": analytics},
            metrics=metrics,
            alerts=alerts,
            status="warning" if alerts else "ok",
        )
        self._store(report)
        return report

    async def generate_persona_report(self, state: dict[str, Any]) -> OperationalReport:
        persona_outputs = state.get("persona_outputs", [])
        active_personas = state.get("active_personas", [])

        metrics: dict[str, float] = {
            "personas_activated": float(len(active_personas)),
            "persona_outputs_generated": float(len(persona_outputs)),
        }
        alerts = []
        if len(active_personas) == 0:
            alerts.append("No personas activated — check persona recommendation engine")

        report = OperationalReport(
            report_type=OperationalReportType.PERSONA,
            title="Persona Activation Report",
            summary=f"{len(active_personas)} persona(s) activated, {len(persona_outputs)} output(s) generated",
            data={
                "active_personas": active_personas,
                "persona_outputs_summary": [
                    {"persona_id": p.get("persona_id"), "persona_name": p.get("persona_name")}
                    for p in persona_outputs
                ],
            },
            metrics=metrics,
            alerts=alerts,
            recommendations=(
                ["Activate more personas for richer content enrichment"]
                if len(active_personas) < 2 else []
            ),
            status="warning" if alerts else "ok",
        )
        self._store(report)
        return report

    async def generate_analytics_report(self, state: dict[str, Any]) -> OperationalReport:
        analytics = state.get("analytics_report", {})
        approved = state.get("approved_content", [])
        rejected = state.get("rejected_content", [])

        total = len(approved) + len(rejected)
        approval_rate = (len(approved) / total * 100) if total > 0 else 0.0
        metrics = {
            "content_published": float(len(approved)),
            "content_rejected": float(len(rejected)),
            "approval_rate_pct": round(approval_rate, 1),
            "performance_score": float(analytics.get("performance_score", 0)),
            "estimated_reach": float(analytics.get("estimated_reach", 0)),
        }
        alerts = []
        if approval_rate < 50 and total > 0:
            alerts.append(f"Low approval rate {approval_rate:.1f}% — governance thresholds too strict?")

        report = OperationalReport(
            report_type=OperationalReportType.ANALYTICS,
            title="Analytics Performance Report",
            summary=(
                f"Published {len(approved)}/{total} content items "
                f"(approval rate {approval_rate:.1f}%). "
                f"Estimated reach: {int(analytics.get('estimated_reach', 0)):,}."
            ),
            data=analytics,
            metrics=metrics,
            alerts=alerts,
            status="warning" if alerts else "ok",
        )
        self._store(report)
        return report

    async def generate_revenue_report(self, state: dict[str, Any]) -> OperationalReport:
        analytics = state.get("analytics_report", {})
        revenue = analytics.get("revenue_summary", {})

        metrics = {
            "total_opportunity_usd": float(revenue.get("total_opportunity_usd", 0)),
            "signal_count": float(revenue.get("signal_count", 0)),
            "high_value_signals": float(revenue.get("high_value_signals", 0)),
        }
        alerts = []
        if revenue.get("high_value_signals", 0) > 0:
            alerts.append(
                f"{revenue['high_value_signals']} high-value sponsor signal(s) awaiting activation"
            )

        report = OperationalReport(
            report_type=OperationalReportType.REVENUE,
            title="Revenue Intelligence Report",
            summary=(
                f"Total opportunity: ${revenue.get('total_opportunity_usd', 0):,.0f} "
                f"from {revenue.get('signal_count', 0)} signal(s). "
                f"Priority brand: {revenue.get('priority_brand', 'N/A')}."
            ),
            data=revenue,
            metrics=metrics,
            alerts=alerts,
            recommendations=(
                ["Activate high-value sponsor signals this week"]
                if revenue.get("high_value_signals", 0) > 0 else []
            ),
            status="warning" if alerts else "ok",
        )
        self._store(report)
        return report

    async def generate_governance_report(self, state: dict[str, Any]) -> OperationalReport:
        approved = state.get("approved_content", [])
        rejected = state.get("rejected_content", [])
        reviews = state.get("governance_reviews", [])
        total = len(approved) + len(rejected)
        rate = (len(approved) / total * 100) if total > 0 else 100.0

        alerts: list[str] = []
        if rate < 50 and total > 0:
            alerts.append(f"Approval rate {rate:.1f}% below 50% — content quality review needed")

        report = OperationalReport(
            report_type=OperationalReportType.GOVERNANCE,
            title="Governance Compliance Report",
            summary=(
                f"Constitutional gate: {len(approved)} approved / {len(rejected)} rejected "
                f"({rate:.1f}% approval rate)."
            ),
            data={"approved": len(approved), "rejected": len(rejected), "reviews": len(reviews)},
            metrics={
                "approved": float(len(approved)),
                "rejected": float(len(rejected)),
                "approval_rate_pct": round(rate, 1),
            },
            alerts=alerts,
            recommendations=["Review rejected content for root cause patterns"] if rejected else [],
            status="warning" if (rate < 50 and total > 0) else "ok",
        )
        self._store(report)
        return report

    async def generate_infrastructure_report(self, state: dict[str, Any]) -> OperationalReport:
        infra_ready = state.get("infrastructure_ready", False)
        ai_metrics = state.get("ai_metrics", {})

        alerts: list[str] = []
        if not infra_ready:
            alerts.append("Infrastructure not fully initialized")

        report = OperationalReport(
            report_type=OperationalReportType.INFRASTRUCTURE,
            title="Infrastructure Health Report",
            summary=f"Infrastructure ready: {infra_ready}. AI metrics: {len(ai_metrics)} tracked.",
            data={"infrastructure_ready": infra_ready, "ai_metrics": ai_metrics},
            metrics={"infrastructure_ready": float(infra_ready)},
            alerts=alerts,
            status="warning" if alerts else "ok",
        )
        self._store(report)
        return report

    def get_history(
        self, report_type: OperationalReportType | None = None
    ) -> list[dict[str, Any]]:
        reports = self._history
        if report_type:
            reports = [r for r in reports if r.report_type == report_type]
        return [r.to_dict() for r in reports[-100:]]

    def _store(self, report: OperationalReport) -> None:
        self._history.append(report)
        if len(self._history) > 500:
            self._history = self._history[-500:]
