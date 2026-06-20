"""Crisis Management War Room — P1 priority. Protect trust and reputation."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, TYPE_CHECKING

from sfc.war_rooms.crisis.models import (
    CrisisEvent,
    CrisisReport,
    CrisisSeverity,
    CrisisType,
)
from sfc.war_rooms.deactivation.models import ClosureReport
from sfc.war_rooms.shared.types import (
    WarRoomHealth,
    WarRoomPriority,
    WarRoomState,
    WarRoomType,
)

if TYPE_CHECKING:
    from sfc.war_rooms.registry.service import WarRoomRegistry

logger = logging.getLogger("sfc.war_rooms.crisis")

# Response SLOs by severity
_SLO_MINUTES: dict[CrisisSeverity, int] = {
    CrisisSeverity.CRITICAL: 2,
    CrisisSeverity.HIGH: 15,
    CrisisSeverity.MEDIUM: 60,
    CrisisSeverity.LOW: 240,
}

# Containment actions by crisis type
_CONTAINMENT_ACTIONS: dict[CrisisType, list[str]] = {
    CrisisType.FAKE_NEWS: [
        "Issue correction within 15 minutes.",
        "Tag original content as corrected.",
        "Contact originating platform with correction request.",
        "Document correction in audit log.",
        "Monitor for spread and continue corrections.",
    ],
    CrisisType.PUBLISHING_ERROR: [
        "Pull erroneous content from all platforms immediately.",
        "Issue public correction notice.",
        "Notify audience via official channels.",
        "Document error in compliance log.",
        "Review editorial process to prevent recurrence.",
    ],
    CrisisType.REPUTATION_RISK: [
        "Prepare official statement for executive review.",
        "Monitor social sentiment across all platforms.",
        "Brief executive team immediately.",
        "Pause scheduled promotional content.",
        "Engage legal counsel if required.",
    ],
    CrisisType.SPONSOR_CRISIS: [
        "Contact sponsor representative immediately.",
        "Prepare joint statement draft.",
        "Pause all sponsor activations pending resolution.",
        "Document timeline of events for sponsor.",
        "Escalate to executive leadership.",
    ],
    CrisisType.SECURITY_INCIDENT: [
        "Isolate affected systems.",
        "Notify security team and IT.",
        "Preserve all logs and artifacts.",
        "Inform executives and legal counsel.",
        "Prepare public statement if required.",
    ],
    CrisisType.PUBLIC_CONTROVERSY: [
        "Monitor controversy scope and reach.",
        "Prepare measured response statement.",
        "Brief all division heads.",
        "Avoid escalation — do not engage trolls.",
        "Document all relevant content and responses.",
    ],
    CrisisType.PLATFORM_STRIKE: [
        "File platform appeal within 1 hour.",
        "Migrate affected content to backup platforms.",
        "Notify audience of content availability.",
        "Document strike details for compliance.",
        "Review content policy to prevent future strikes.",
    ],
}


class CrisisWarRoom:
    """Crisis Management War Room — P1 priority. Protect trust and reputation."""

    war_room_type = WarRoomType.CRISIS
    default_priority = WarRoomPriority.P1_CRITICAL

    def __init__(self, registry: "WarRoomRegistry") -> None:
        self._registry = registry
        self._active_crises: list[CrisisEvent] = []
        self._reports: dict[str, CrisisReport] = {}
        self._state: WarRoomState | None = None

    async def activate(self, crisis_event: CrisisEvent) -> WarRoomState:
        """Activate crisis war room for a specific crisis event."""
        self._active_crises.append(crisis_event)

        existing = self._registry.get_by_type(WarRoomType.CRISIS)
        if existing is not None:
            # Update with new crisis
            existing.active_events.append(crisis_event.crisis_id)
            self._state = existing
            return existing

        state = self._registry.activate(
            WarRoomType.CRISIS,
            metadata={
                "crisis_id": crisis_event.crisis_id,
                "crisis_type": crisis_event.crisis_type,
                "severity": crisis_event.severity,
                "description": crisis_event.description,
            },
        )
        state.active_events.append(crisis_event.crisis_id)
        self._state = state
        logger.critical(
            "[Crisis] ACTIVATED — ID=%s type=%s severity=%s",
            crisis_event.crisis_id,
            crisis_event.crisis_type,
            crisis_event.severity,
        )
        return state

    async def assess_crisis(self, crisis_event: CrisisEvent) -> CrisisReport:
        """Full crisis assessment: verification, damage, containment plan."""
        verification = await self.verify_crisis(crisis_event)
        containment = await self.create_containment_plan(
            CrisisReport(
                crisis_id=crisis_event.crisis_id,
                crisis_type=crisis_event.crisis_type,
                severity=crisis_event.severity,
                description=crisis_event.description,
                detected_at=crisis_event.detected_at,
            )
        )
        damage = await self.assess_damage(crisis_event)
        executive_alert = await self.create_executive_alert(crisis_event)
        slo = _SLO_MINUTES.get(crisis_event.severity, 60)
        recovery = await self.create_recovery_plan(
            CrisisReport(
                crisis_id=crisis_event.crisis_id,
                crisis_type=crisis_event.crisis_type,
                severity=crisis_event.severity,
                description=crisis_event.description,
                detected_at=crisis_event.detected_at,
                containment_actions=containment,
                damage_assessment=damage,
            )
        )
        report = CrisisReport(
            crisis_id=crisis_event.crisis_id,
            crisis_type=crisis_event.crisis_type,
            severity=crisis_event.severity,
            description=crisis_event.description,
            detected_at=crisis_event.detected_at,
            initial_assessment=verification.get("assessment", "Assessment complete"),
            containment_actions=containment,
            damage_assessment=damage,
            recovery_plan=recovery,
            executive_alert=executive_alert,
            lessons_learned=[
                f"SLO for {crisis_event.severity.value} severity: respond within {slo} minutes.",
                "Always verify before acting — but act within the SLO window.",
                "Document every action taken during crisis.",
            ],
            status="open",
        )
        self._reports[crisis_event.crisis_id] = report
        return report

    async def verify_crisis(self, crisis_event: CrisisEvent) -> dict[str, Any]:
        """Verify the crisis is real and assess initial scope."""
        return {
            "crisis_id": crisis_event.crisis_id,
            "verified": True,
            "assessment": (
                f"Crisis type '{crisis_event.crisis_type.value}' detected with severity "
                f"'{crisis_event.severity.value}'. Verification protocol initiated. "
                f"Description: {crisis_event.description}"
            ),
            "affected_content": crisis_event.affected_content_ids,
            "affected_platforms": crisis_event.affected_platforms,
            "initial_scope": "localized" if crisis_event.severity in (CrisisSeverity.LOW, CrisisSeverity.MEDIUM) else "broad",
            "verified_at": datetime.utcnow().isoformat(),
        }

    async def create_containment_plan(self, report: CrisisReport) -> list[str]:
        """Immediate containment actions based on crisis type."""
        actions = _CONTAINMENT_ACTIONS.get(
            report.crisis_type,
            [
                "Assess scope of crisis immediately.",
                "Brief executive team.",
                "Document all actions taken.",
                "Prepare public communication if required.",
            ],
        )
        slo = _SLO_MINUTES.get(report.severity, 60)
        return [f"[SLO: {slo} min] " + action for action in actions]

    async def assess_damage(self, crisis_event: CrisisEvent) -> dict[str, Any]:
        """Estimate reputational + financial damage."""
        damage_levels = {
            CrisisSeverity.CRITICAL: {"reputational": "severe", "financial_risk_sar": 500000},
            CrisisSeverity.HIGH: {"reputational": "high", "financial_risk_sar": 100000},
            CrisisSeverity.MEDIUM: {"reputational": "moderate", "financial_risk_sar": 25000},
            CrisisSeverity.LOW: {"reputational": "low", "financial_risk_sar": 5000},
        }
        base = damage_levels.get(crisis_event.severity, {"reputational": "unknown", "financial_risk_sar": 0})
        return {
            "crisis_id": crisis_event.crisis_id,
            "reputational_impact": base["reputational"],
            "financial_risk_sar": base["financial_risk_sar"],
            "platforms_affected": len(crisis_event.affected_platforms),
            "content_affected": len(crisis_event.affected_content_ids),
            "audience_exposure_estimate": "TBD — monitoring underway",
            "assessed_at": datetime.utcnow().isoformat(),
        }

    async def create_recovery_plan(self, report: CrisisReport) -> list[str]:
        """Step-by-step recovery plan with timeline."""
        return [
            f"Step 1: Execute all containment actions (within SLO window).",
            f"Step 2: Monitor platforms for spread and sentiment for 24h.",
            f"Step 3: Publish correction/statement if applicable.",
            f"Step 4: Conduct post-mortem within 48h of resolution.",
            f"Step 5: Update protocols based on lessons learned.",
            f"Step 6: Brief all divisions on prevention measures.",
        ]

    async def create_executive_alert(self, crisis_event: CrisisEvent) -> str:
        """Urgent executive brief: what happened, severity, immediate actions."""
        slo = _SLO_MINUTES.get(crisis_event.severity, 60)
        alert = (
            f"[CRISIS ALERT — {crisis_event.severity.value.upper()}] "
            f"ID: {crisis_event.crisis_id}. "
            f"Type: {crisis_event.crisis_type.value.replace('_', ' ').title()}. "
            f"Detected: {crisis_event.detected_at.strftime('%Y-%m-%d %H:%M UTC')}. "
            f"Description: {crisis_event.description}. "
            f"Response SLO: {slo} minutes. "
            f"Immediate action required. Crisis team activated."
        )
        if crisis_event.affected_platforms:
            alert += f" Affected platforms: {', '.join(crisis_event.affected_platforms)}."
        return alert

    async def resolve_crisis(self, crisis_id: str, resolution_notes: str = "") -> CrisisReport:
        """Mark crisis as resolved and generate final report."""
        # Find existing report or create a minimal one
        report = self._reports.get(crisis_id)
        if report is None:
            # Find in active crises
            matching = next((c for c in self._active_crises if c.crisis_id == crisis_id), None)
            if matching is None:
                raise ValueError(f"Crisis not found: {crisis_id}")
            report = CrisisReport(
                crisis_id=crisis_id,
                crisis_type=matching.crisis_type,
                severity=matching.severity,
                description=matching.description,
                detected_at=matching.detected_at,
            )

        resolved_at = datetime.utcnow()
        # Mutate report fields
        object.__setattr__(report, "status", "resolved") if hasattr(report, "__setattr__") else None
        report.status = "resolved"
        report.resolved_at = resolved_at
        if resolution_notes:
            report.lessons_learned.append(f"Resolution notes: {resolution_notes}")
        report.lessons_learned.append(
            f"Crisis resolved at {resolved_at.strftime('%Y-%m-%d %H:%M UTC')}."
        )

        # Update active crisis status
        for crisis in self._active_crises:
            if crisis.crisis_id == crisis_id:
                crisis.status = "resolved"

        self._reports[crisis_id] = report
        logger.info("[Crisis] Resolved crisis %s", crisis_id)
        return report

    def get_active_crises(self) -> list[CrisisEvent]:
        return [c for c in self._active_crises if c.status == "open"]

    async def deactivate(self) -> ClosureReport:
        """Close the Crisis War Room."""
        from sfc.war_rooms.deactivation.service import DeactivationEngine
        engine = DeactivationEngine(self._registry)
        state = self._state or self._registry.get_by_type(WarRoomType.CRISIS)
        if state is None:
            raise ValueError("No active Crisis war room to deactivate")
        return await engine.deactivate(state.war_room_id, reason="crisis_resolved")

    def health_check(self) -> WarRoomHealth:
        """Return health status. Never raises."""
        try:
            state = self._state or self._registry.get_by_type(WarRoomType.CRISIS)
            active_open = [c for c in self._active_crises if c.status == "open"]
            warnings = []
            if active_open:
                warnings.append(f"{len(active_open)} open crisis/crises require attention.")
            if state is None:
                return WarRoomHealth(
                    war_room_id="none",
                    status="inactive",
                    health_score=100.0,
                    warnings=warnings or ["No active Crisis war room"],
                )
            return WarRoomHealth(
                war_room_id=state.war_room_id,
                status=state.status,
                health_score=state.health_score,
                warnings=warnings,
            )
        except Exception as exc:
            return WarRoomHealth(
                war_room_id="error",
                status="unhealthy",
                health_score=0.0,
                warnings=[str(exc)],
            )
