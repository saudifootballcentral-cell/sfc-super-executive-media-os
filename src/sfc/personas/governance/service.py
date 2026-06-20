from __future__ import annotations

import logging
from datetime import datetime

from sfc.personas.shared.types import PersonaProfile, PersonaStatus
from sfc.personas.governance.models import (
    ApprovalRecord,
    GovernanceCheck,
    GovernanceCheckType,
    GovernanceReport,
)

logger = logging.getLogger("sfc.personas.governance")


class PersonaGovernanceFramework:
    """Governance and compliance framework for personas."""

    def __init__(self) -> None:
        pass

    async def review(self, persona: PersonaProfile) -> GovernanceReport:
        """Run 5 governance checks on a persona."""
        checks: list[GovernanceCheck] = []

        # 1. Prompt validation: description length > 20
        desc_len = len(persona.description)
        prompt_check = GovernanceCheck(
            check_type=GovernanceCheckType.PROMPT_VALIDATION,
            passed=desc_len > 20,
            score=min(100.0, float(desc_len)),
            notes=f"Description length: {desc_len}",
        )
        checks.append(prompt_check)

        # 2. Capability validation: >= 2 capabilities
        cap_count = len(persona.capabilities)
        cap_check = GovernanceCheck(
            check_type=GovernanceCheckType.CAPABILITY_VALIDATION,
            passed=cap_count >= 2,
            score=min(100.0, float(cap_count * 20)),
            notes=f"Capabilities count: {cap_count}",
        )
        checks.append(cap_check)

        # 3. Performance validation: score >= 60
        perf_check = GovernanceCheck(
            check_type=GovernanceCheckType.PERFORMANCE_VALIDATION,
            passed=persona.performance_score >= 60,
            score=persona.performance_score,
            notes=f"Performance score: {persona.performance_score}",
        )
        checks.append(perf_check)

        # 4. Risk assessment: always passes for ACTIVE personas
        risk_passed = persona.status == PersonaStatus.ACTIVE
        risk_score_val = max(0.0, 100.0 - persona.performance_score)
        risk_check = GovernanceCheck(
            check_type=GovernanceCheckType.RISK_ASSESSMENT,
            passed=risk_passed,
            score=max(0.0, 100.0 - risk_score_val),
            notes=f"Risk score: {risk_score_val:.1f}",
        )
        checks.append(risk_check)

        # 5. Compliance review: passes if not RETIRED
        compliance_passed = persona.status != PersonaStatus.RETIRED
        compliance_check = GovernanceCheck(
            check_type=GovernanceCheckType.COMPLIANCE_REVIEW,
            passed=compliance_passed,
            score=100.0 if compliance_passed else 0.0,
            notes=f"Status: {persona.status.value}",
        )
        checks.append(compliance_check)

        overall_passed = all(c.passed for c in checks)

        # Risk score = mean of (100 - check.score) for failed checks, else 0
        failed_checks = [c for c in checks if not c.passed]
        if failed_checks:
            risk_score = sum(100.0 - c.score for c in failed_checks) / len(failed_checks)
        else:
            risk_score = 0.0

        compliance_notes = [c.notes for c in checks if not c.passed]

        report = GovernanceReport(
            persona_id=persona.persona_id,
            checks=checks,
            overall_passed=overall_passed,
            risk_score=risk_score,
            compliance_notes=compliance_notes,
            reviewed_at=datetime.utcnow(),
        )
        logger.info(
            "[PersonaGovernanceFramework] Reviewed %s: passed=%s, risk=%.1f",
            persona.persona_id, overall_passed, risk_score,
        )
        return report

    async def approve(
        self, persona: PersonaProfile, approver: str = "governance_framework"
    ) -> ApprovalRecord:
        """Review persona and issue approval record."""
        report = await self.review(persona)
        approved = report.overall_passed
        rationale = (
            "All governance checks passed."
            if approved
            else f"Failed checks: {[c.check_type.value for c in report.checks if not c.passed]}"
        )

        return ApprovalRecord(
            persona_id=persona.persona_id,
            approved=approved,
            approver=approver,
            rationale=rationale,
            approved_at=datetime.utcnow(),
        )

    async def assess_risk(self, persona: PersonaProfile) -> dict:
        """Return risk assessment with level and mitigation steps."""
        report = await self.review(persona)
        risk_score = report.risk_score

        if risk_score < 20:
            risk_level = "low"
        elif risk_score < 50:
            risk_level = "medium"
        else:
            risk_level = "high"

        mitigation_steps: list[str] = []
        if risk_level == "high":
            mitigation_steps = [
                "Increase performance score through targeted training",
                "Expand capability set",
                "Review and update persona description",
            ]
        elif risk_level == "medium":
            mitigation_steps = [
                "Monitor performance trend",
                "Consider capability expansion",
            ]
        else:
            mitigation_steps = ["Continue current operations"]

        return {
            "persona_id": persona.persona_id,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "mitigation_steps": mitigation_steps,
        }

    def health_check(self) -> dict:
        """Return health status."""
        return {
            "component": "PersonaGovernanceFramework",
            "status": "healthy",
            "metrics": {
                "check_types": len(GovernanceCheckType),
            },
        }
