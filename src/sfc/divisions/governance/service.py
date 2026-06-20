"""Governance Division — main service implementation.

Wraps the constitutional review logic from governance_node and exposes it
as a proper DivisionInterface service.
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime
from typing import Any

from sfc.core.constitution import get_governance_rules
from sfc.core.models import Division
from sfc.divisions.base import (
    DivisionHealth,
    DivisionInput,
    DivisionOutput,
    DivisionReport,
    ValidationResult,
)
from sfc.divisions.governance.interface import GovernanceDivisionInterface
from sfc.divisions.governance.models import GovernanceOutput
from sfc.events.bus import get_event_bus
from sfc.events.types import BaseEvent, EscalationRequired, GovernanceApproved, GovernanceRejected
from sfc.memory.division_memory import DivisionMemory

logger = logging.getLogger("sfc.divisions.governance.service")


class GovernanceService(GovernanceDivisionInterface):
    """Governance Division — constitutional compliance gate."""

    division = Division.GOVERNANCE

    def __init__(self, memory_store: DivisionMemory | None = None) -> None:
        self.memory = memory_store
        self._rules = get_governance_rules()
        self._call_count = 0
        self._error_count = 0
        self._total_processing_ms = 0.0
        self._total_approved = 0
        self._total_rejected = 0
        self._total_escalated = 0

    async def initialize(self) -> None:
        self._rules = get_governance_rules()
        logger.info("[Governance] Initialized with rules: %s", self._rules)

    async def shutdown(self) -> None:
        logger.info("[Governance] Shutdown")

    async def execute(self, input: DivisionInput) -> DivisionOutput:
        start = time.monotonic()
        self._call_count += 1
        try:
            state = input.state_snapshot
            content_drafts = state.get("content_drafts", [])

            approved: list[dict[str, Any]] = []
            rejected: list[dict[str, Any]] = []
            reviews: list[dict[str, Any]] = []
            events: list[BaseEvent] = []

            for draft in content_drafts:
                review = await self.review_content(draft)
                reviews.append(review)

                if review["approved"]:
                    approved.append({**draft, "governance_approved_at": datetime.utcnow().isoformat()})
                    self._total_approved += 1
                    events.append(GovernanceApproved(
                        division=self.division.value,
                        run_id=input.run_id,
                        payload={"content_id": draft.get("content_id"), "title": draft.get("title", "")[:60]},
                    ))
                else:
                    rejected.append({
                        **draft,
                        "governance_rejected_at": datetime.utcnow().isoformat(),
                        "rejection_reasons": review["reasons"],
                    })
                    self._total_rejected += 1
                    events.append(GovernanceRejected(
                        division=self.division.value,
                        run_id=input.run_id,
                        payload={"content_id": draft.get("content_id"), "reasons": review["reasons"]},
                    ))

                if review.get("escalated"):
                    self._total_escalated += 1
                    events.append(EscalationRequired(
                        division=self.division.value,
                        run_id=input.run_id,
                        priority="high",
                        payload={"content_id": draft.get("content_id"), "reasons": review["reasons"]},
                    ))

            if self.memory:
                self.memory.set(f"reviews_{input.run_id}", reviews)

            get_event_bus().publish_many(events)

            elapsed = (time.monotonic() - start) * 1000
            self._total_processing_ms += elapsed

            return GovernanceOutput(
                run_id=input.run_id,
                division=self.division.value,
                success=True,
                data={
                    "governance_reviews": reviews,
                    "approved_content": approved,
                    "rejected_content": rejected,
                    "pipeline_stage": "governance_complete",
                },
                events_to_publish=events,
                processing_time_ms=elapsed,
                governance_reviews=reviews,
                approved_content=approved,
                rejected_content=rejected,
            )
        except Exception as exc:
            self._error_count += 1
            logger.error("[Governance] execute() failed: %s", exc, exc_info=True)
            return DivisionOutput(
                run_id=input.run_id,
                division=self.division.value,
                success=False,
                errors=[str(exc)],
                processing_time_ms=(time.monotonic() - start) * 1000,
            )

    async def review_content(self, draft: dict[str, Any]) -> dict[str, Any]:
        """Full constitutional review of a content draft."""
        compliance = await self.check_constitutional_compliance(draft)
        reasons = compliance.get("violations", [])
        escalated = compliance.get("escalated", False)
        return {
            "content_id": draft.get("content_id"),
            "title": draft.get("title", "")[:80],
            "approved": len(reasons) == 0,
            "escalated": escalated,
            "reasons": reasons,
            "scores": draft.get("scores", {}),
            "reviewed_at": datetime.utcnow().isoformat(),
        }

    async def check_constitutional_compliance(self, draft: dict[str, Any]) -> dict[str, Any]:
        """Run all constitutional checks and return violations list."""
        rules = self._rules
        violations: list[str] = []
        escalated = False
        scores = draft.get("scores", {})

        confidence = float(scores.get("confidence_score", 0.0))
        source_count = int(scores.get("source_count", 0))
        brand_alignment = float(scores.get("brand_alignment_score", 100.0))
        risk_score = float(scores.get("risk_score", 0.0))
        is_rumor = draft.get("is_rumor", False)
        rumor_label = draft.get("rumor_label", "")

        if source_count < rules["min_source_count"]:
            violations.append(
                f"Insufficient sources: {source_count} provided, {int(rules['min_source_count'])} required."
            )

        if confidence < rules["min_confidence_score"]:
            violations.append(
                f"Confidence score {confidence:.1f} below threshold {rules['min_confidence_score']}. Escalated."
            )
            escalated = True

        if brand_alignment < rules["min_brand_alignment_score"]:
            violations.append(
                f"Brand alignment {brand_alignment:.1f} below threshold {rules['min_brand_alignment_score']}."
            )

        if risk_score > rules["max_risk_score_before_escalation"]:
            violations.append(
                f"High risk score {risk_score:.1f} > {rules['max_risk_score_before_escalation']} — flagged for review."
            )
            escalated = True

        if is_rumor and not rumor_label:
            violations.append("Rumor detected but not labeled. Must include rumor disclaimer.")

        return {
            "violations": violations,
            "escalated": escalated,
            "checks_run": ["source_count", "confidence", "brand_alignment", "risk", "rumor_policy"],
        }

    async def escalate(self, draft: dict[str, Any], reasons: list[str]) -> str:
        """Flag content for executive review. Returns escalation ticket ID."""
        ticket_id = f"ESC-{uuid.uuid4().hex[:8].upper()}"
        if self.memory:
            self.memory.set(f"escalation_{ticket_id}", {
                "content_id": draft.get("content_id"),
                "reasons": reasons,
                "created_at": datetime.utcnow().isoformat(),
            })
        logger.warning("[Governance] ESCALATED %s | reasons: %s", ticket_id, reasons)
        return ticket_id

    async def handle_event(self, event: BaseEvent) -> None:
        from sfc.divisions.governance.handlers import HANDLERS
        handler = HANDLERS.get(event.event_type)
        if handler:
            await handler(event, self)

    async def validate(self, content: dict[str, Any]) -> ValidationResult:
        compliance = await self.check_constitutional_compliance(content)
        violations = compliance.get("violations", [])
        score = max(0.0, 100.0 - len(violations) * 20.0)
        return ValidationResult(
            valid=len(violations) == 0,
            score=score,
            reasons=violations,
            suggestions=["Fix violations and resubmit for governance review"],
        )

    async def report(self) -> DivisionReport:
        pass_rate = (
            self._total_approved / (self._total_approved + self._total_rejected)
            if (self._total_approved + self._total_rejected) > 0
            else 0.0
        )
        return DivisionReport(
            division=self.division.value,
            period="session",
            metrics={
                "total_approved": self._total_approved,
                "total_rejected": self._total_rejected,
                "total_escalated": self._total_escalated,
                "pass_rate": round(pass_rate, 3),
            },
            highlights=[f"{self._total_approved} pieces approved, {self._total_rejected} rejected"],
            recommendations=["Review escalated content within 2 hours"],
        )

    def health_check(self) -> DivisionHealth:
        return DivisionHealth(
            division=self.division.value,
            status="healthy",
            metrics={
                "call_count": self._call_count,
                "approved": self._total_approved,
                "rejected": self._total_rejected,
                "escalated": self._total_escalated,
            },
        )

    def describe(self) -> str:
        return "Compliance, fact-checking, risk management, and brand safety"
