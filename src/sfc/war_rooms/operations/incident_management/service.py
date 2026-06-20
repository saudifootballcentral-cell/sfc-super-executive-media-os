"""Incident Management Engine — service implementation."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sfc.events.bus import get_event_bus
from sfc.war_rooms.operations.incident_management.models import (
    Incident,
    IncidentSeverity,
    IncidentStatus,
    IncidentType,
    Postmortem,
    RecoveryPlan,
)
from sfc.war_rooms.shared.events import IncidentDetected, IncidentResolved

logger = logging.getLogger("sfc.war_rooms.operations.incident_management")

_RECOVERY_STEPS: dict[IncidentType, list[str]] = {
    IncidentType.PLATFORM_FAILURE: [
        "Identify affected platform services",
        "Failover to backup systems",
        "Notify platform team",
        "Monitor recovery metrics",
        "Restore normal operations",
    ],
    IncidentType.PUBLISHING_FAILURE: [
        "Halt scheduled publishing queue",
        "Diagnose publishing pipeline failure",
        "Apply content queue fix",
        "Resume publishing",
        "Verify content delivery",
    ],
    IncidentType.AGENT_FAILURE: [
        "Isolate failing agent",
        "Redirect tasks to healthy agents",
        "Restart agent process",
        "Validate agent health",
        "Resume normal workload",
    ],
    IncidentType.TOOL_FAILURE: [
        "Identify failing tool",
        "Switch to fallback tool",
        "Diagnose root cause",
        "Apply fix or update",
        "Restore primary tool",
    ],
    IncidentType.DATA_FAILURE: [
        "Halt data-dependent processes",
        "Assess data integrity",
        "Restore from last known good snapshot",
        "Validate data consistency",
        "Resume dependent processes",
    ],
    IncidentType.SECURITY_INCIDENT: [
        "IMMEDIATE: Isolate affected systems",
        "Revoke compromised credentials",
        "Notify security team",
        "Conduct forensic analysis",
        "Restore secure configuration",
        "Issue security advisory",
    ],
    IncidentType.GOVERNANCE_FAILURE: [
        "Suspend affected content publishing",
        "Conduct compliance review",
        "Escalate to governance team",
        "Apply corrective action",
        "Resume with additional controls",
    ],
}


class IncidentManagementEngine:
    """Engine for detecting, containing, recovering, and resolving operational incidents."""

    def __init__(self) -> None:
        self._incidents: dict[str, Incident] = {}
        self._executive_alert_system: Any = None  # Lazy import to avoid circular deps

    def _get_executive_alert_system(self) -> Any:
        if self._executive_alert_system is None:
            from sfc.war_rooms.operations.executive_alerts.service import ExecutiveAlertSystem
            self._executive_alert_system = ExecutiveAlertSystem()
        return self._executive_alert_system

    async def detect(
        self,
        incident_type: IncidentType,
        severity: IncidentSeverity,
        title: str,
        description: str,
        impact: str,
        affected_components: list[str],
    ) -> Incident:
        """Detect and register a new incident."""
        incident = Incident(
            incident_type=incident_type,
            severity=severity,
            status=IncidentStatus.DETECTED,
            title=title,
            description=description,
            impact=impact,
            affected_components=affected_components,
            detected_at=datetime.utcnow(),
            timeline=[{
                "timestamp": datetime.utcnow().isoformat(),
                "event": "incident_detected",
                "notes": description,
            }],
        )
        self._incidents[incident.incident_id] = incident

        get_event_bus().publish(
            IncidentDetected(
                division="operations",
                run_id=incident.incident_id,
                payload={
                    "incident_id": incident.incident_id,
                    "incident_type": incident_type.value,
                    "severity": severity.value,
                    "title": title,
                    "impact": impact,
                },
            )
        )

        # For P1/P2 raise an executive alert
        if severity in (IncidentSeverity.P1, IncidentSeverity.P2):
            from sfc.war_rooms.operations.executive_alerts.models import (
                AlertCategory,
                AlertSeverity,
            )
            eas = self._get_executive_alert_system()
            exec_severity = AlertSeverity.CRITICAL if severity == IncidentSeverity.P1 else AlertSeverity.HIGH
            await eas.raise_alert(
                category=AlertCategory.SYSTEM_FAILURE,
                severity=exec_severity,
                title=f"[{severity.value.upper()}] {title}",
                summary=f"Incident detected: {description}. Impact: {impact}",
                action_required=True,
                recommended_action="Initiate incident response immediately",
                context={"incident_id": incident.incident_id, "severity": severity.value},
            )

        logger.warning(
            "[Incident] Detected %s [%s]: %s", incident.incident_id, severity.value, title
        )
        return incident

    async def contain(self, incident_id: str, containment_notes: str) -> Incident:
        """Mark an incident as contained."""
        incident = self._get_incident(incident_id)
        incident.status = IncidentStatus.CONTAINED
        incident.contained_at = datetime.utcnow()
        incident.timeline.append({
            "timestamp": datetime.utcnow().isoformat(),
            "event": "incident_contained",
            "notes": containment_notes,
        })
        logger.info("[Incident] Contained: %s", incident_id)
        return incident

    async def recover(self, incident_id: str) -> RecoveryPlan:
        """Generate a recovery plan for the incident and update its status."""
        incident = self._get_incident(incident_id)
        incident.status = IncidentStatus.RECOVERING
        incident.timeline.append({
            "timestamp": datetime.utcnow().isoformat(),
            "event": "recovery_started",
            "notes": "Recovery plan initiated",
        })

        steps = _RECOVERY_STEPS.get(incident.incident_type, [
            "Assess situation",
            "Apply standard recovery procedure",
            "Validate recovery",
            "Resume normal operations",
        ])
        p1_p2 = incident.severity in (IncidentSeverity.P1, IncidentSeverity.P2)
        estimated = 15 if incident.severity == IncidentSeverity.P1 else 30 if p1_p2 else 60

        plan = RecoveryPlan(
            incident_id=incident_id,
            steps=steps,
            estimated_recovery_minutes=estimated,
            created_at=datetime.utcnow(),
        )
        logger.info("[Incident] Recovery plan created for: %s", incident_id)
        return plan

    async def resolve(self, incident_id: str, root_cause: str) -> Incident:
        """Mark an incident as resolved."""
        incident = self._get_incident(incident_id)
        incident.status = IncidentStatus.RESOLVED
        incident.resolved_at = datetime.utcnow()
        incident.root_cause = root_cause
        incident.timeline.append({
            "timestamp": datetime.utcnow().isoformat(),
            "event": "incident_resolved",
            "notes": f"Root cause: {root_cause}",
        })

        get_event_bus().publish(
            IncidentResolved(
                division="operations",
                run_id=incident_id,
                payload={
                    "incident_id": incident_id,
                    "root_cause": root_cause,
                    "resolved_at": incident.resolved_at.isoformat(),
                },
            )
        )
        logger.info("[Incident] Resolved: %s — %s", incident_id, root_cause)
        return incident

    async def create_postmortem(self, incident_id: str) -> Postmortem:
        """Create a postmortem report for a resolved incident."""
        incident = self._get_incident(incident_id)
        postmortem = Postmortem(
            incident_id=incident_id,
            title=f"Postmortem: {incident.title}",
            summary=(
                f"{incident.severity.value.upper()} {incident.incident_type.value} incident "
                f"detected at {incident.detected_at.strftime('%Y-%m-%d %H:%M UTC')}."
            ),
            timeline=incident.timeline,
            root_cause=incident.root_cause or "Under investigation",
            contributing_factors=[
                f"Affected components: {', '.join(incident.affected_components)}",
            ],
            impact_assessment=incident.impact,
            lessons_learned=[
                "Review monitoring thresholds",
                "Update runbooks",
                "Add automated recovery steps",
            ],
            action_items=[
                "Update incident response playbook",
                "Schedule team retrospective",
                "Implement preventive measures",
            ],
            created_at=datetime.utcnow(),
        )
        incident.status = IncidentStatus.POSTMORTEM
        logger.info("[Incident] Postmortem created for: %s", incident_id)
        return postmortem

    def get_open_incidents(self) -> list[Incident]:
        """Return all incidents not yet resolved or in postmortem."""
        closed = (IncidentStatus.RESOLVED, IncidentStatus.POSTMORTEM)
        return [i for i in self._incidents.values() if i.status not in closed]

    def health_check(self) -> dict[str, Any]:
        return {
            "component": "incident_management_engine",
            "status": "healthy",
            "total_incidents": len(self._incidents),
            "open_incidents": len(self.get_open_incidents()),
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_incident(self, incident_id: str) -> Incident:
        incident = self._incidents.get(incident_id)
        if incident is None:
            raise ValueError(f"Incident not found: {incident_id}")
        return incident
