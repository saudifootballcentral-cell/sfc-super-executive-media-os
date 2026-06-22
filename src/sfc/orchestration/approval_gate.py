"""ApprovalGate — triple-lock enforcement before live publishing."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sfc.orchestration.master_state import ApprovalRecord, MasterState, RunStatus


class ApprovalDeniedError(Exception):
    """Raised when the gate refuses to pass content to live publishing."""


@dataclass
class GateDecision:
    approved: bool
    reason: str
    checks: dict[str, bool]
    decided_at: datetime = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.decided_at is None:
            self.decided_at = datetime.utcnow()

    def to_dict(self) -> dict[str, Any]:
        return {
            "approved": self.approved,
            "reason": self.reason,
            "checks": self.checks,
            "decided_at": self.decided_at.isoformat(),
        }


class ApprovalGate:
    """Triple-lock gate that must pass before live content is published.

    Three independent locks must ALL be True:
      1. governance_approved  — set by the governance division inside the graph
      2. operator_approved    — set by a human operator via grant_operator_approval()
      3. LIVE_PUBLISHING_ENABLED env var  — environment-level kill switch

    Additionally, if dry_run=True on MasterState, the gate always soft-blocks
    (returns approved=False with reason "dry_run_mode"), so no actual publishing
    occurs but no error is raised — callers skip publishing gracefully.
    """

    def evaluate(self, state: MasterState) -> GateDecision:
        """Return a GateDecision. Does NOT raise — callers decide what to do."""
        if state.dry_run:
            return GateDecision(
                approved=False,
                reason="dry_run_mode",
                checks={
                    "dry_run": True,
                    "governance_approved": state.approval.governance_approved,
                    "operator_approved": state.approval.operator_approved,
                    "live_publishing_enabled": self._live_enabled(),
                },
            )

        checks = {
            "dry_run": False,
            "governance_approved": state.approval.governance_approved,
            "operator_approved": state.approval.operator_approved,
            "live_publishing_enabled": self._live_enabled(),
        }
        all_passed = (
            checks["governance_approved"]
            and checks["operator_approved"]
            and checks["live_publishing_enabled"]
        )
        if all_passed:
            reason = "all_checks_passed"
        else:
            failed = [k for k, v in checks.items() if not v]
            reason = f"blocked_by:{','.join(failed)}"

        return GateDecision(approved=all_passed, reason=reason, checks=checks)

    def enforce(self, state: MasterState) -> None:
        """Evaluate and raise ApprovalDeniedError if publishing should be blocked."""
        decision = self.evaluate(state)
        if not decision.approved:
            raise ApprovalDeniedError(
                f"Publishing blocked — {decision.reason}. Checks: {decision.checks}"
            )

    def grant_operator_approval(
        self,
        state: MasterState,
        granted_by: str = "operator",
        reason: str = "",
    ) -> None:
        state.approval.operator_approved = True
        state.approval.granted_at = datetime.utcnow()
        state.approval.granted_by = granted_by
        state.approval.reason = reason
        state.status = RunStatus.APPROVED
        state.append_history("operator_approval_granted", {"granted_by": granted_by, "reason": reason})

    def deny_operator_approval(
        self,
        state: MasterState,
        denied_by: str = "operator",
        reason: str = "",
    ) -> None:
        state.approval.operator_approved = False
        state.approval.denied_at = datetime.utcnow()
        state.approval.denied_by = denied_by
        state.approval.reason = reason
        state.status = RunStatus.ABORTED
        state.append_history("operator_approval_denied", {"denied_by": denied_by, "reason": reason})

    def set_governance_approved(self, state: MasterState, approved: bool) -> None:
        state.approval.governance_approved = approved

    @staticmethod
    def _live_enabled() -> bool:
        return os.environ.get("LIVE_PUBLISHING_ENABLED", "false").lower() == "true"
