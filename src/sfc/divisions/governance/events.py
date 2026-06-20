"""Governance Division — event definitions."""

from __future__ import annotations

from sfc.events.types import EscalationRequired, GovernanceApproved, GovernanceRejected

SUBSCRIBED_EVENTS: list[str] = ["content_draft_created", "story_created"]
PUBLISHED_EVENTS: list[str] = ["governance_approved", "governance_rejected", "escalation_required"]

__all__ = [
    "SUBSCRIBED_EVENTS", "PUBLISHED_EVENTS",
    "GovernanceApproved", "GovernanceRejected", "EscalationRequired",
]
