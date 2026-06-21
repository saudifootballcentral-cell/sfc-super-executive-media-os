"""SFCState — the single typed state object that flows through the entire LangGraph pipeline."""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


class SFCState(TypedDict):
    """Shared state for the SFC Super Executive LangGraph pipeline.

    Execution order:
        super_executive → planning → [PARALLEL: intelligence + analytics_background + revenue_background]
        → editorial → creative → governance → publishing → analytics → learning → memory_update → END

    Parallel phase:
        intelligence, analytics_background, revenue_background all run simultaneously.
        analytics_background and revenue_background write to their own keys with no conflicts.
        The final analytics node acts as the join point (waits for publishing + both background nodes).
    """

    # -----------------------------------------------------------------------
    # INPUT — set before the graph runs
    # -----------------------------------------------------------------------
    run_id: str
    task_type: str          # TaskType enum value
    task_payload: dict[str, Any]

    # -----------------------------------------------------------------------
    # STAGE TRACKING
    # -----------------------------------------------------------------------
    pipeline_stage: str
    started_at: str
    completed_at: str | None

    # -----------------------------------------------------------------------
    # NODE: super_executive
    # Claude analyzes the task and makes the routing decision.
    # -----------------------------------------------------------------------
    executive_decision: dict[str, Any]

    # -----------------------------------------------------------------------
    # NODE: planning
    # Converts the executive decision into a detailed execution plan.
    # -----------------------------------------------------------------------
    execution_plan: dict[str, Any]

    # -----------------------------------------------------------------------
    # PARALLEL PHASE — all three nodes start simultaneously after planning
    # -----------------------------------------------------------------------

    # NODE: intelligence  (parallel #1, main — feeds editorial)
    intelligence_report: dict[str, Any]
    verified_sources: list[dict[str, Any]]

    # NODE: analytics_background  (parallel #2, independent)
    # Analyzes historical performance data — results consumed by analytics (final)
    analytics_background_data: dict[str, Any]

    # NODE: revenue_background  (parallel #3, independent)
    # Scans for monetization signals — results stored in state for publishing/planning
    revenue_signals: list[dict[str, Any]]

    # -----------------------------------------------------------------------
    # SEQUENTIAL MAIN CHAIN (starts after intelligence completes)
    # -----------------------------------------------------------------------

    # NODE: editorial
    content_drafts: list[dict[str, Any]]

    # NODE: creative
    creative_assets: list[dict[str, Any]]

    # NODE: governance
    governance_reviews: list[dict[str, Any]]
    approved_content: list[dict[str, Any]]
    rejected_content: list[dict[str, Any]]

    # NODE: publishing
    publish_queue: list[dict[str, Any]]
    publish_results: dict[str, Any]

    # -----------------------------------------------------------------------
    # NODE: analytics  (JOIN — waits for publishing + analytics_background + revenue_background)
    # -----------------------------------------------------------------------
    analytics_report: dict[str, Any]

    # -----------------------------------------------------------------------
    # NODE: learning
    # -----------------------------------------------------------------------
    lessons_learned: list[str]

    # -----------------------------------------------------------------------
    # NODE: memory_update
    # -----------------------------------------------------------------------
    memory_update_log: list[dict[str, Any]]

    # -----------------------------------------------------------------------
    # NODE: war_room_router  (between super_executive and planning)
    # -----------------------------------------------------------------------
    war_room_state: dict[str, Any]

    # -----------------------------------------------------------------------
    # NODE: persona_layer  (between editorial and creative)
    # -----------------------------------------------------------------------
    active_personas: list[str]
    persona_outputs: list[dict[str, Any]]

    # -----------------------------------------------------------------------
    # INFRASTRUCTURE
    # -----------------------------------------------------------------------
    infrastructure_ready: bool

    # -----------------------------------------------------------------------
    # ACCUMULATED WITH REDUCERS (safe for parallel writes)
    # -----------------------------------------------------------------------
    errors: Annotated[list[str], operator.add]
    warnings: Annotated[list[str], operator.add]


def make_initial_state(
    task_type: str,
    task_payload: dict[str, Any],
    run_id: str | None = None,
) -> SFCState:
    """Create a fully-initialised SFCState ready to enter the graph."""
    import uuid
    from datetime import datetime

    return SFCState(
        run_id=run_id or str(uuid.uuid4()),
        task_type=task_type,
        task_payload=task_payload,
        pipeline_stage="init",
        started_at=datetime.utcnow().isoformat(),
        completed_at=None,
        executive_decision={},
        execution_plan={},
        intelligence_report={},
        verified_sources=[],
        analytics_background_data={},
        revenue_signals=[],
        content_drafts=[],
        creative_assets=[],
        governance_reviews=[],
        approved_content=[],
        rejected_content=[],
        publish_queue=[],
        publish_results={},
        analytics_report={},
        lessons_learned=[],
        memory_update_log=[],
        war_room_state={},
        active_personas=[],
        persona_outputs=[],
        infrastructure_ready=False,
        errors=[],
        warnings=[],
    )
