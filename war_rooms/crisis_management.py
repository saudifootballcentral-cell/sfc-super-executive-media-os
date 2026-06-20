"""Crisis Management War Room — brand protection and rapid response."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from core.models import WarRoom
from war_rooms.base import BaseWarRoom

SEVERITY_LEVELS = ["low", "medium", "high", "critical"]


class CrisisManagementWarRoom(BaseWarRoom):
    """Activated when a brand crisis, misinformation outbreak, or sensitive event occurs.

    Responsibilities:
    - Rapid assessment
    - Response strategy
    - Statement drafting
    - Publishing decisions
    - Monitoring resolution
    """

    war_room = WarRoom.CRISIS_MANAGEMENT

    def _on_activate(self, context: dict[str, Any]) -> None:
        self.crisis_context = context
        self.severity = context.get("severity", "medium")
        self.responses: list[dict[str, Any]] = []
        self.publishing_hold = True
        self.record("crisis_declared", context)
        self.logger.critical(
            "[Crisis] CRISIS DECLARED — severity=%s: %s",
            self.severity,
            context.get("description", "No description"),
        )

    def _on_deactivate(self, summary: dict[str, Any]) -> None:
        self.publishing_hold = False
        self.record("crisis_resolved", summary)
        self.logger.info("[Crisis] Crisis resolved")

    def draft_response(self, statement: str, channel: str, approved: bool = False) -> dict[str, Any]:
        response = {
            "statement": statement,
            "channel": channel,
            "approved": approved,
            "drafted_at": datetime.utcnow().isoformat(),
        }
        self.responses.append(response)
        self.record("response_drafted", response)
        return response

    def approve_response(self, response_index: int) -> bool:
        if 0 <= response_index < len(self.responses):
            self.responses[response_index]["approved"] = True
            return True
        return False

    def lift_publishing_hold(self) -> None:
        self.publishing_hold = False
        self.record("publishing_hold_lifted")
        self.logger.info("[Crisis] Publishing hold lifted")

    def get_crisis_report(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "context": self.crisis_context,
            "publishing_hold_active": self.publishing_hold,
            "responses_drafted": len(self.responses),
            "approved_responses": len([r for r in self.responses if r["approved"]]),
            "activated_at": self.activated_at.isoformat() if self.activated_at else None,
        }
