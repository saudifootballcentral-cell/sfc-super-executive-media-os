"""LangGraph node functions for War Room Operations & Control Layer.

These are standalone async node functions NOT wired into the main graph.
They are available for future integration via graph composition or subgraphs.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("sfc.graph.nodes.war_room_operations")


async def breaking_news_node(state: dict[str, Any]) -> dict[str, Any]:
    """Node: breaking_news — detect and package breaking news events."""
    from sfc.war_rooms.operations.breaking_news.service import BreakingNewsCommandCenter

    run_id = state.get("run_id", "")
    payload = state.get("task_payload", {})
    headline = payload.get("headline", "Breaking News Event")
    sources = payload.get("sources", [])
    metadata = payload.get("metadata", {})

    service = BreakingNewsCommandCenter()
    try:
        alert = await service.detect(headline=headline, sources=sources, metadata=metadata)
        package = await service.package_news(alert)
        logger.info("[Node:BreakingNews] Alert %s packaged | run_id=%s", alert.alert_id, run_id)
        return {
            "breaking_news_alert": alert.model_dump(),
            "news_package": package.model_dump(),
            "pipeline_stage": "breaking_news_complete",
        }
    except Exception as exc:
        logger.error("[Node:BreakingNews] Failed: %s", exc, exc_info=True)
        return {"errors": [f"BREAKING_NEWS: {exc}"], "pipeline_stage": "breaking_news_failed"}


async def live_operations_node(state: dict[str, Any]) -> dict[str, Any]:
    """Node: live_operations — take an operational snapshot."""
    from sfc.war_rooms.operations.live_operations.service import LiveOperationsCommand

    run_id = state.get("run_id", "")
    service = LiveOperationsCommand()
    try:
        snapshot = await service.snapshot()
        report = await service.report()
        logger.info("[Node:LiveOps] Snapshot %s taken | run_id=%s", snapshot.snapshot_id, run_id)
        return {
            "operations_snapshot": snapshot.model_dump(),
            "operations_report": report,
            "pipeline_stage": "live_operations_complete",
        }
    except Exception as exc:
        logger.error("[Node:LiveOps] Failed: %s", exc, exc_info=True)
        return {"errors": [f"LIVE_OPERATIONS: {exc}"], "pipeline_stage": "live_operations_failed"}


async def monitoring_node(state: dict[str, Any]) -> dict[str, Any]:
    """Node: monitoring — scan all domains and report health."""
    from sfc.war_rooms.operations.monitoring.service import RealTimeMonitoringCenter

    run_id = state.get("run_id", "")
    service = RealTimeMonitoringCenter()
    try:
        health_report = await service.scan_all_domains()
        trend_report = await service.get_trend_report()
        logger.info(
            "[Node:Monitoring] Health=%.1f | run_id=%s",
            health_report.overall_health,
            run_id,
        )
        return {
            "health_report": health_report.model_dump(),
            "trend_report": trend_report.model_dump(),
            "pipeline_stage": "monitoring_complete",
        }
    except Exception as exc:
        logger.error("[Node:Monitoring] Failed: %s", exc, exc_info=True)
        return {"errors": [f"MONITORING: {exc}"], "pipeline_stage": "monitoring_failed"}


async def escalation_node(state: dict[str, Any]) -> dict[str, Any]:
    """Node: escalation — evaluate context and trigger escalations if needed."""
    from sfc.war_rooms.operations.escalation.service import EscalationFramework

    run_id = state.get("run_id", "")
    payload = state.get("task_payload", {})
    context: dict[str, Any] = {
        "confidence_score": payload.get("confidence_score", 100),
        "risk_score": payload.get("risk_score", 0),
        "compliance_risk": payload.get("compliance_risk", False),
        "brand_risk": payload.get("brand_risk", False),
        "system_failure": payload.get("system_failure", False),
        "security_risk": payload.get("security_risk", False),
    }

    service = EscalationFramework()
    try:
        record = await service.evaluate(context)
        logger.info(
            "[Node:Escalation] Evaluation complete — escalated=%s | run_id=%s",
            record is not None,
            run_id,
        )
        return {
            "escalation_record": record.model_dump() if record else None,
            "escalated": record is not None,
            "pipeline_stage": "escalation_complete",
        }
    except Exception as exc:
        logger.error("[Node:Escalation] Failed: %s", exc, exc_info=True)
        return {"errors": [f"ESCALATION: {exc}"], "pipeline_stage": "escalation_failed"}


async def executive_alert_node(state: dict[str, Any]) -> dict[str, Any]:
    """Node: executive_alert — generate an executive summary from current alerts."""
    from sfc.war_rooms.operations.executive_alerts.service import ExecutiveAlertSystem

    run_id = state.get("run_id", "")
    service = ExecutiveAlertSystem()
    try:
        summary = await service.generate_summary()
        logger.info(
            "[Node:ExecutiveAlert] Summary generated | run_id=%s", run_id
        )
        return {
            "executive_summary": summary.model_dump(),
            "pipeline_stage": "executive_alert_complete",
        }
    except Exception as exc:
        logger.error("[Node:ExecutiveAlert] Failed: %s", exc, exc_info=True)
        return {"errors": [f"EXECUTIVE_ALERT: {exc}"], "pipeline_stage": "executive_alert_failed"}


async def coordination_node(state: dict[str, Any]) -> dict[str, Any]:
    """Node: coordination — build a coordination plan for active war rooms."""
    from sfc.war_rooms.operations.coordination.service import CrossWarRoomCoordinator
    from sfc.war_rooms.shared.types import WarRoomPriority, WarRoomState, WarRoomType

    run_id = state.get("run_id", "")
    # Build active states from state payload if provided
    active_war_rooms_raw: list[dict[str, Any]] = state.get("active_war_rooms", [])
    active_states: list[WarRoomState] = []
    for raw in active_war_rooms_raw:
        try:
            active_states.append(WarRoomState(**raw))
        except Exception:
            pass

    service = CrossWarRoomCoordinator()
    try:
        plan = await service.coordinate(active_states)
        logger.info(
            "[Node:Coordination] Plan %s | mode=%s | run_id=%s",
            plan.plan_id,
            plan.mode.value,
            run_id,
        )
        return {
            "coordination_plan": plan.model_dump(),
            "pipeline_stage": "coordination_complete",
        }
    except Exception as exc:
        logger.error("[Node:Coordination] Failed: %s", exc, exc_info=True)
        return {"errors": [f"COORDINATION: {exc}"], "pipeline_stage": "coordination_failed"}


async def incident_management_node(state: dict[str, Any]) -> dict[str, Any]:
    """Node: incident_management — detect and triage an incident from payload."""
    from sfc.war_rooms.operations.incident_management.models import (
        IncidentSeverity,
        IncidentType,
    )
    from sfc.war_rooms.operations.incident_management.service import IncidentManagementEngine

    run_id = state.get("run_id", "")
    payload = state.get("task_payload", {})

    # Only create incident if payload contains incident data
    if not payload.get("incident_type"):
        return {"pipeline_stage": "incident_management_skipped"}

    service = IncidentManagementEngine()
    try:
        incident_type = IncidentType(payload.get("incident_type", "agent_failure"))
        severity = IncidentSeverity(payload.get("severity", "p3"))
        incident = await service.detect(
            incident_type=incident_type,
            severity=severity,
            title=payload.get("title", "Detected Incident"),
            description=payload.get("description", "Incident detected via pipeline"),
            impact=payload.get("impact", "Unknown impact"),
            affected_components=payload.get("affected_components", []),
        )
        recovery_plan = await service.recover(incident.incident_id)
        logger.info(
            "[Node:IncidentMgmt] %s detected [%s] | run_id=%s",
            incident.incident_id,
            severity.value,
            run_id,
        )
        return {
            "incident": incident.model_dump(),
            "recovery_plan": recovery_plan.model_dump(),
            "pipeline_stage": "incident_management_complete",
        }
    except Exception as exc:
        logger.error("[Node:IncidentMgmt] Failed: %s", exc, exc_info=True)
        return {"errors": [f"INCIDENT_MANAGEMENT: {exc}"], "pipeline_stage": "incident_management_failed"}


async def dashboard_node(state: dict[str, Any]) -> dict[str, Any]:
    """Node: dashboard — build the executive dashboard."""
    from sfc.war_rooms.operations.dashboards.models import DashboardType
    from sfc.war_rooms.operations.dashboards.service import OperationalDashboardLayer

    run_id = state.get("run_id", "")
    dashboard_type_str = state.get("task_payload", {}).get("dashboard_type", "executive")
    service = OperationalDashboardLayer()
    try:
        dashboard_type = DashboardType(dashboard_type_str)
        dashboard = await service.build(dashboard_type)
        logger.info(
            "[Node:Dashboard] %s dashboard built | run_id=%s",
            dashboard_type.value,
            run_id,
        )
        return {
            "dashboard": dashboard.model_dump(),
            "pipeline_stage": "dashboard_complete",
        }
    except Exception as exc:
        logger.error("[Node:Dashboard] Failed: %s", exc, exc_info=True)
        return {"errors": [f"DASHBOARD: {exc}"], "pipeline_stage": "dashboard_failed"}
