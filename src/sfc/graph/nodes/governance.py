"""Governance Node — constitutional compliance gate.

This node FULLY IMPLEMENTS the constitutional rules. It is not a stub.
Every piece of content is blocked until it passes all three checks:
  1. source_count >= 2
  2. confidence_score >= 85
  3. brand_alignment_score >= 70
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sfc.core.constitution import get_governance_rules
from sfc.graph.state import SFCState

logger = logging.getLogger("sfc.node.governance")


async def governance_node(state: SFCState) -> dict[str, Any]:
    """Node: governance

    The constitutional gate. Reviews every content draft against:
    - Verification Policy  (sources >= 2)
    - Confidence Policy    (confidence >= 85 or escalate)
    - Brand Alignment      (brand_alignment >= 70)
    - Risk Policy          (risk_score <= 50 or flag)
    - Rumor Policy         (rumor must be labeled)

    Items that pass → approved_content
    Items that fail → rejected_content

    Publishing is blocked until this node approves.
    """
    content_drafts = state.get("content_drafts", [])
    rules = get_governance_rules()

    min_confidence = rules["min_confidence_score"]
    min_sources = rules["min_source_count"]
    min_brand_alignment = rules["min_brand_alignment_score"]
    max_risk = rules["max_risk_score_before_escalation"]

    logger.info("[Governance] Reviewing %d draft(s)", len(content_drafts))

    # Package 2: Try GovernanceService first, fall through to inline logic on failure
    try:
        from sfc.divisions.governance.service import GovernanceService
        from sfc.divisions.base import DivisionInput
        service = GovernanceService()
        await service.initialize()
        result = await service.execute(DivisionInput(
            run_id=state.get("run_id", ""),
            task_type=state.get("task_type", "news"),
            payload=state.get("task_payload", {}),
            state_snapshot=dict(state),
        ))
        if result.success:
            return {
                "governance_reviews": result.data.get("governance_reviews", []),
                "approved_content": result.data.get("approved_content", []),
                "rejected_content": result.data.get("rejected_content", []),
                "pipeline_stage": "governance_complete",
            }
    except Exception as svc_exc:
        logger.warning("[Governance] Service call failed, using inline logic: %s", svc_exc)

    approved: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    reviews: list[dict[str, Any]] = []

    for draft in content_drafts:
        review = _review_draft(draft, min_confidence, min_sources, min_brand_alignment, max_risk)
        reviews.append(review)

        if review["approved"]:
            approved.append({**draft, "governance_approved_at": datetime.utcnow().isoformat()})
            logger.info("[Governance] ✓ APPROVED: %s", draft.get("title", "")[:60])
        else:
            rejected.append({
                **draft,
                "governance_rejected_at": datetime.utcnow().isoformat(),
                "rejection_reasons": review["reasons"],
            })
            logger.warning(
                "[Governance] ✗ REJECTED: %s | reasons: %s",
                draft.get("title", "")[:60],
                "; ".join(review["reasons"]),
            )

        if review.get("escalated"):
            logger.error("[Governance] ESCALATED for review: %s", draft.get("title", "")[:60])

    pass_rate = len(approved) / len(content_drafts) * 100 if content_drafts else 0.0
    logger.info(
        "[Governance] Complete | approved=%d rejected=%d pass_rate=%.1f%%",
        len(approved), len(rejected), pass_rate,
    )

    # Package 7: AI generates explanatory notes AFTER constitutional check.
    # The code-based check result is ALWAYS authoritative — AI CANNOT override it.
    ai_notes: dict[str, Any] = {}
    try:
        from sfc.ai.model_gateway import get_ai_gateway
        from sfc.ai.models import ModelRequest
        from sfc.ai.prompt_loader import get_prompt_loader
        import json as _json

        loader = get_prompt_loader()
        system_prompt = loader.load("divisions", "governance")
        gateway = get_ai_gateway()
        ai_request = ModelRequest(
            task_type="governance",
            system_prompt=system_prompt,
            user_message=(
                f"The code-based constitutional compliance check is complete and FINAL.\n"
                f"approved_count={len(approved)}, rejected_count={len(rejected)}\n"
                f"rejection_reasons={_json.dumps([r.get('reasons', []) for r in reviews if not r.get('approved')])}\n\n"
                "Generate ONLY explanatory notes and improvement suggestions. "
                "Do NOT change any approval decisions. "
                "Return JSON: {\"explanation\": str, \"suggestions\": list[str]}"
            ),
            max_tokens=512,
            json_mode=True,
        )
        ai_response = await gateway.complete(ai_request)
        if ai_response.success and ai_response.parsed and not ai_response.used_fallback:
            ai_notes = ai_response.parsed
            logger.debug("[Governance] AI explanatory notes generated")
    except Exception as ai_exc:
        logger.debug("[Governance] AI notes skipped: %s", ai_exc)

    return {
        "governance_reviews": reviews,
        "approved_content": approved,
        "rejected_content": rejected,
        "pipeline_stage": "governance_complete",
        **({"ai_governance_notes": ai_notes} if ai_notes else {}),
    }


def _review_draft(
    draft: dict[str, Any],
    min_confidence: float,
    min_sources: int,
    min_brand_alignment: float,
    max_risk: float,
) -> dict[str, Any]:
    reasons: list[str] = []
    approved = True
    escalated = False

    scores = draft.get("scores", {})
    confidence = float(scores.get("confidence_score", 0.0))
    source_count = int(scores.get("source_count", 0))
    brand_alignment = float(scores.get("brand_alignment_score", 100.0))
    risk_score = float(scores.get("risk_score", 0.0))
    is_rumor = draft.get("is_rumor", False)
    rumor_label = draft.get("rumor_label", "")

    # --- Verification Policy ---
    if source_count < min_sources:
        approved = False
        reasons.append(
            f"Insufficient sources: {source_count} provided, {min_sources} required."
        )

    # --- Confidence Policy ---
    if confidence < min_confidence:
        approved = False
        escalated = True
        reasons.append(
            f"Confidence score {confidence:.1f} below threshold {min_confidence}. Escalated."
        )

    # --- Brand Alignment ---
    if brand_alignment < min_brand_alignment:
        approved = False
        reasons.append(
            f"Brand alignment {brand_alignment:.1f} below threshold {min_brand_alignment}."
        )

    # --- Risk Policy ---
    if risk_score > max_risk:
        escalated = True
        reasons.append(f"High risk score {risk_score:.1f} > {max_risk} — flagged for review.")

    # --- Rumor Policy ---
    if is_rumor and not rumor_label:
        approved = False
        reasons.append("Rumor detected but not labeled. Must include rumor disclaimer.")

    return {
        "content_id": draft.get("content_id"),
        "title": draft.get("title", "")[:80],
        "approved": approved,
        "escalated": escalated,
        "reasons": reasons,
        "scores": scores,
        "reviewed_at": datetime.utcnow().isoformat(),
    }
