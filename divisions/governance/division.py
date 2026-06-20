"""Governance Division — enforces verification policy, confidence thresholds, and brand rules."""

from __future__ import annotations

import logging
from typing import Any

from core.models import ContentItem, ContentStatus, Division, OutputScores, SFCEvent
from divisions.base import BaseDivision

logger = logging.getLogger("sfc.division.governance")

MINIMUM_SOURCES = 2
MINIMUM_CONFIDENCE = 85.0
MINIMUM_BRAND_ALIGNMENT = 70.0


class GovernanceReview:
    def __init__(
        self,
        approved: bool,
        content_id: str,
        reasons: list[str],
        escalated: bool = False,
    ) -> None:
        self.approved = approved
        self.content_id = content_id
        self.reasons = reasons
        self.escalated = escalated

    def to_dict(self) -> dict[str, Any]:
        return {
            "approved": self.approved,
            "content_id": self.content_id,
            "reasons": self.reasons,
            "escalated": self.escalated,
        }


class GovernanceDivision(BaseDivision):
    """Gate-keeper that enforces the constitution's publishing policy.

    Publishing is prohibited until:
    - Research Complete
    - Verification Complete (min 2 sources)
    - Confidence Score >= 85
    - Brand Alignment >= 70
    - Governance Approved
    """

    division = Division.GOVERNANCE

    async def handle_event(self, event: SFCEvent) -> dict[str, Any] | None:
        return None

    def review_content(self, content: ContentItem) -> GovernanceReview:
        reasons: list[str] = []
        approved = True
        escalated = False

        if len(content.sources) < MINIMUM_SOURCES:
            approved = False
            reasons.append(
                f"Insufficient sources: {len(content.sources)} provided, {MINIMUM_SOURCES} required."
            )

        scores: OutputScores | None = content.scores
        if scores is None:
            approved = False
            reasons.append("Missing OutputScores — content cannot be evaluated.")
        else:
            if scores.confidence_score < MINIMUM_CONFIDENCE:
                approved = False
                escalated = True
                reasons.append(
                    f"Confidence score {scores.confidence_score:.1f} below threshold {MINIMUM_CONFIDENCE}."
                )
            if scores.brand_alignment_score < MINIMUM_BRAND_ALIGNMENT:
                approved = False
                reasons.append(
                    f"Brand alignment {scores.brand_alignment_score:.1f} below threshold {MINIMUM_BRAND_ALIGNMENT}."
                )
            if scores.risk_score > 50.0:
                escalated = True
                reasons.append(f"High risk score: {scores.risk_score:.1f} — escalated for review.")

        if approved:
            content.status = ContentStatus.APPROVED
            self.logger.info("[Governance] APPROVED content %s", content.content_id)
        else:
            content.status = ContentStatus.REJECTED
            self.logger.warning(
                "[Governance] REJECTED content %s: %s",
                content.content_id,
                "; ".join(reasons),
            )

        review = GovernanceReview(
            approved=approved,
            content_id=str(content.content_id),
            reasons=reasons,
            escalated=escalated,
        )
        self.memory.set(f"review:{content.content_id}", review.to_dict())
        return review

    def review_payload(self, scores: OutputScores, source_count: int) -> GovernanceReview:
        """Review raw scores without a full ContentItem."""
        reasons: list[str] = []
        approved = True
        escalated = False

        if source_count < MINIMUM_SOURCES:
            approved = False
            reasons.append(f"Need {MINIMUM_SOURCES} sources, got {source_count}.")

        if scores.confidence_score < MINIMUM_CONFIDENCE:
            approved = False
            escalated = True
            reasons.append(f"Confidence {scores.confidence_score:.1f} < {MINIMUM_CONFIDENCE}.")

        if scores.brand_alignment_score < MINIMUM_BRAND_ALIGNMENT:
            approved = False
            reasons.append(f"Brand alignment {scores.brand_alignment_score:.1f} < {MINIMUM_BRAND_ALIGNMENT}.")

        return GovernanceReview(
            approved=approved,
            content_id="payload_review",
            reasons=reasons,
            escalated=escalated,
        )
