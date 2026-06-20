"""LangGraph node functions for infrastructure post-processing.

These functions are NOT inserted into the main graph automatically.
They can be called FROM within existing division nodes when needed,
or added to the graph by users who want the infrastructure post-processing pass.

Available nodes:
- infrastructure_node: Full post-processing (learning + KG update + audit + memory persist)
- agentops_health_node: AgentOps health check and audit snapshot
- simulation_node: Run scenario simulations for the current state
"""

from __future__ import annotations

import logging
from typing import Any

from sfc.graph.state import SFCState
from sfc.infrastructure.context import init_infrastructure

logger = logging.getLogger("sfc.graph.nodes.infrastructure")


async def infrastructure_node(state: SFCState) -> dict[str, Any]:
    """Infrastructure post-processing: learning + observability + KG update.

    Runs AFTER memory_update as a "cleanup + learning" pass.
    Returns updates to lessons_learned and pipeline_stage.
    """
    ctx = await init_infrastructure()
    run_id = state.get("run_id", "unknown")

    logger.info("[InfraNode] Running infrastructure post-processing for run %s", run_id)

    # 1. Feed completed workflow to learning engine
    try:
        lessons = await ctx.learning_engine.analyze_workflow(dict(state))
    except Exception as exc:  # noqa: BLE001
        logger.error("[InfraNode] Learning engine error: %s", exc)
        lessons = []

    # 2. Update knowledge graph from intelligence report
    intel_report = state.get("intelligence_report", {})
    if intel_report:
        try:
            entity_count = await ctx.knowledge_graph.ingest_intelligence_report(intel_report)
            logger.info("[InfraNode] KG ingested %d entities from intelligence report", entity_count)
        except Exception as exc:  # noqa: BLE001
            logger.error("[InfraNode] KG ingest error: %s", exc)

    # 3. Record run cost/audit to agentops
    try:
        ctx.agentops.audit(
            "infrastructure",
            "workflow_complete",
            run_id,
            payload={
                "task_type": state.get("task_type", "unknown"),
                "pipeline_stage": state.get("pipeline_stage", "unknown"),
                "approved_count": len(state.get("approved_content", [])),
                "rejected_count": len(state.get("rejected_content", [])),
                "lessons_count": len(lessons),
            },
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("[InfraNode] AgentOps audit error: %s", exc)

    # 4. Persist lessons to memory
    for lesson in lessons:
        try:
            await ctx.memory_manager.store(
                "lessons",
                lesson.lesson_id.hex,
                lesson.model_dump(),
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("[InfraNode] Memory persist error for lesson %s: %s", lesson.lesson_id, exc)

    new_lesson_observations = [l.observation for l in lessons]

    logger.info(
        "[InfraNode] Completed for run %s: %d new lessons", run_id, len(lessons)
    )

    return {
        "lessons_learned": new_lesson_observations,
        "pipeline_stage": "infrastructure_complete",
    }


async def agentops_health_node(state: SFCState) -> dict[str, Any]:
    """AgentOps health check and snapshot — can be called from any node."""
    ctx = await init_infrastructure()
    run_id = state.get("run_id", "unknown")

    try:
        health_report = ctx.agentops.health_report()
        cost_report = ctx.agentops.cost_report()
        optimization_tips = ctx.agentops.optimization_report()

        ctx.agentops.audit(
            "agentops",
            "health_check",
            run_id,
            payload={
                "components_checked": len(health_report),
                "total_cost_usd": cost_report.get("total_cost_usd", 0.0),
                "optimizations": len(optimization_tips),
            },
        )

        logger.info(
            "[AgentOpsHealthNode] Health check complete: %d components", len(health_report)
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("[AgentOpsHealthNode] Error: %s", exc)

    return {
        "pipeline_stage": "agentops_health_checked",
    }


async def simulation_node(state: SFCState) -> dict[str, Any]:
    """Run scenario simulations for the current state.

    Uses the simulation engine to predict content performance before publishing.
    Results are stored in the state's analytics_report.
    """
    ctx = await init_infrastructure()
    run_id = state.get("run_id", "unknown")

    from sfc.infrastructure.simulation_engine.models import SimulationScenario

    task_type = state.get("task_type", "news")
    execution_plan = state.get("execution_plan", {})
    platforms = execution_plan.get("platforms", ["youtube", "instagram_reels", "tiktok"])
    content_type = execution_plan.get("content_type", "video")

    try:
        # Simulate content performance
        result = await ctx.simulation_engine.simulate_content_performance(
            content_type=content_type,
            platforms=platforms if isinstance(platforms, list) else [str(platforms)],
            task_type=task_type,
            confidence_score=85.0,
            source_count=len(state.get("verified_sources", [])) or 2,
        )

        logger.info(
            "[SimulationNode] Simulated: reach=%d score=%.1f risk=%.1f",
            result.expected_reach,
            result.overall_score,
            result.risk_score,
        )

        return {
            "pipeline_stage": "simulation_complete",
            "analytics_report": {
                **state.get("analytics_report", {}),
                "simulation": result.model_dump(),
                "predicted_reach": result.expected_reach,
                "predicted_revenue_usd": result.expected_revenue_usd,
            },
        }
    except Exception as exc:  # noqa: BLE001
        logger.error("[SimulationNode] Simulation error: %s", exc)
        return {
            "pipeline_stage": "simulation_skipped",
            "errors": [f"Simulation error: {exc}"],
        }
