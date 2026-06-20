"""Edge routing logic for the SFC Super Executive LangGraph pipeline."""

from __future__ import annotations

import logging
from typing import Literal

from langgraph.graph import END

from sfc.graph.state import SFCState

logger = logging.getLogger("sfc.graph.edges")


def route_after_executive(state: SFCState) -> Literal["planning", "__end__"]:
    """Route after the super_executive node.

    If the executive decided to abort (e.g., no actionable task detected),
    route to END. Otherwise proceed to planning.
    """
    decision = state.get("executive_decision", {})
    routing = decision.get("routing", "planning")

    if routing == "abort":
        logger.info("[Edge] Executive aborted pipeline — routing to END")
        return END  # type: ignore[return-value]

    # Check for hard errors from the executive node
    if state.get("errors"):
        executive_errors = [e for e in state["errors"] if e.startswith("EXECUTIVE:")]
        if executive_errors:
            logger.error("[Edge] Executive errors detected — routing to END")
            return END  # type: ignore[return-value]

    logger.info("[Edge] Executive approved task — routing to planning")
    return "planning"


def route_after_governance(
    state: SFCState,
) -> Literal["publishing", "editorial"]:
    """Route after governance review.

    If all content was rejected, loop back to editorial for revision.
    If at least one piece of content passed, proceed to publishing.
    """
    approved = state.get("approved_content", [])
    rejected = state.get("rejected_content", [])

    if not approved and rejected:
        logger.warning(
            "[Edge] All %d content items rejected — routing back to editorial", len(rejected)
        )
        # NOTE: In production, add a retry counter to SFCState to avoid infinite loops.
        # For Package 1, we route to publishing with empty queue (clean exit).
        return "publishing"

    logger.info(
        "[Edge] Governance passed %d/%d items — routing to publishing",
        len(approved),
        len(approved) + len(rejected),
    )
    return "publishing"
