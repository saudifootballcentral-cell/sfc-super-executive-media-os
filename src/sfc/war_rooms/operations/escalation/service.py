"""Escalation Framework — service implementation."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sfc.events.bus import get_event_bus
from sfc.war_rooms.operations.escalation.models import (
    EscalationLevel,
    EscalationRecord,
    EscalationReport,
    EscalationTrigger,
)
from sfc.war_rooms.shared.events import EscalationResolved, EscalationTriggered

logger = logging.getLogger("sfc.war_rooms.operations.escalation")


class EscalationFramework:
    """Framework for evaluating, creating, and resolving escalations."""

    def __init__(self) -> None:
        self._records: dict[str, EscalationRecord] = {}

    async def evaluate(self, context: dict[str, Any]) -> EscalationRecord | None:
        """Evaluate a context dict against escalation triggers.

        Returns an EscalationRecord if any trigger fires, else None.
        """
        record: EscalationRecord | None = None

        # Check triggers in priority order (most severe first)
        if context.get("system_failure"):
            record = self._build_record(
                trigger=EscalationTrigger.SYSTEM_FAILURE,
                level=EscalationLevel.L4_CRITICAL,
                title="System Failure Detected",
                description="A system failure has been detected requiring immediate intervention.",
                context=context,
                decision_required=True,
            )
        elif context.get("security_risk"):
            record = self._build_record(
                trigger=EscalationTrigger.SECURITY_RISK,
                level=EscalationLevel.L4_CRITICAL,
                title="Security Risk Detected",
                description="A security risk requires immediate executive attention.",
                context=context,
                decision_required=True,
            )
        elif context.get("compliance_risk"):
            record = self._build_record(
                trigger=EscalationTrigger.COMPLIANCE_RISK,
                level=EscalationLevel.L3_EXECUTIVE,
                title="Compliance Risk Identified",
                description="A compliance risk requires executive review.",
                context=context,
                decision_required=True,
            )
        elif context.get("risk_score", 0) > 50:
            record = self._build_record(
                trigger=EscalationTrigger.HIGH_RISK,
                level=EscalationLevel.L3_EXECUTIVE,
                title="High Risk Score",
                description=f"Risk score {context.get('risk_score')} exceeds threshold of 50.",
                context=context,
                decision_required=False,
            )
        elif context.get("brand_risk"):
            record = self._build_record(
                trigger=EscalationTrigger.BRAND_RISK,
                level=EscalationLevel.L2_STRATEGIC,
                title="Brand Risk Detected",
                description="Content or action poses a brand risk.",
                context=context,
                decision_required=True,
            )
        elif context.get("confidence_score", 100) < 85:
            record = self._build_record(
                trigger=EscalationTrigger.LOW_CONFIDENCE,
                level=EscalationLevel.L2_STRATEGIC,
                title="Low Confidence Score",
                description=(
                    f"Confidence score {context.get('confidence_score')} is below threshold of 85."
                ),
                context=context,
                decision_required=False,
            )

        if record is not None:
            self._records[record.escalation_id] = record
            get_event_bus().publish(
                EscalationTriggered(
                    division="operations",
                    run_id=record.escalation_id,
                    payload={
                        "escalation_id": record.escalation_id,
                        "trigger": record.trigger.value,
                        "level": record.level.value,
                        "title": record.title,
                    },
                )
            )
            logger.warning(
                "[Escalation] %s escalation: %s [%s]",
                record.level.value,
                record.title,
                record.trigger.value,
            )

        return record

    async def resolve(self, escalation_id: str, resolution: str) -> EscalationRecord:
        """Mark an escalation as resolved."""
        record = self._records.get(escalation_id)
        if record is None:
            raise ValueError(f"Escalation not found: {escalation_id}")

        record.resolved = True
        record.resolved_at = datetime.utcnow()
        record.resolution = resolution

        get_event_bus().publish(
            EscalationResolved(
                division="operations",
                run_id=escalation_id,
                payload={
                    "escalation_id": escalation_id,
                    "resolution": resolution,
                    "resolved_at": record.resolved_at.isoformat(),
                },
            )
        )
        logger.info("[Escalation] Resolved: %s — %s", escalation_id, resolution)
        return record

    async def report(self, period: str = "session") -> EscalationReport:
        """Generate an escalation report for the current session."""
        all_records = list(self._records.values())
        by_level: dict[str, int] = {}
        by_trigger: dict[str, int] = {}
        resolution_times: list[float] = []

        for r in all_records:
            by_level[r.level.value] = by_level.get(r.level.value, 0) + 1
            by_trigger[r.trigger.value] = by_trigger.get(r.trigger.value, 0) + 1
            if r.resolved and r.resolved_at:
                delta = (r.resolved_at - r.raised_at).total_seconds() / 60.0
                resolution_times.append(delta)

        avg_res = sum(resolution_times) / len(resolution_times) if resolution_times else 0.0
        open_escalations = [r for r in all_records if not r.resolved]

        return EscalationReport(
            period=period,
            total_escalations=len(all_records),
            by_level=by_level,
            by_trigger=by_trigger,
            avg_resolution_time_minutes=round(avg_res, 2),
            open_escalations=open_escalations,
        )

    def get_open_escalations(self) -> list[EscalationRecord]:
        """Return all open (unresolved) escalations."""
        return [r for r in self._records.values() if not r.resolved]

    def health_check(self) -> dict[str, Any]:
        return {
            "component": "escalation_framework",
            "status": "healthy",
            "total_escalations": len(self._records),
            "open_escalations": len(self.get_open_escalations()),
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_record(
        self,
        trigger: EscalationTrigger,
        level: EscalationLevel,
        title: str,
        description: str,
        context: dict[str, Any],
        decision_required: bool = False,
    ) -> EscalationRecord:
        return EscalationRecord(
            trigger=trigger,
            level=level,
            title=title,
            description=description,
            context=context,
            raised_at=datetime.utcnow(),
            decision_required=decision_required,
        )
