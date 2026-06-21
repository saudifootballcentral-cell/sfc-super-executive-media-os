"""Strategic Planning Node — converts executive decision into execution plan.

Runs AFTER planning_node (or replaces planning in the pipeline).
The StrategicPlanningService provides the canonical ICE-scored, division-aware plan.
"""

from __future__ import annotations

import logging
from typing import Any

from sfc.graph.state import SFCState

logger = logging.getLogger("sfc.node.strategic_planning")


async def strategic_planning_node(state: SFCState) -> dict[str, Any]:
    """Node: strategic_planning

    Translates the executive decision into a structured execution plan using
    StrategicPlanningService. Falls back to a minimal plan dict on error.

    Returns: execution_plan (merged/enriched)
    """
    task_type = state.get("task_type", "news")
    payload = state.get("task_payload", {})
    decision = state.get("executive_decision", {})

    logger.info("[StrategicPlanning] Building execution plan | task=%s", task_type)

    # Package 7: Try AI gateway enhancement first
    try:
        from sfc.ai.model_gateway import get_ai_gateway
        from sfc.ai.models import ModelRequest
        from sfc.ai.prompt_loader import get_prompt_loader
        import json as _json

        loader = get_prompt_loader()
        system_prompt = loader.load("divisions", "strategic_planning")
        gateway = get_ai_gateway()
        request = ModelRequest(
            task_type="strategic_planning",
            system_prompt=system_prompt,
            user_message=(
                f"Build an execution plan for this task:\n"
                f"task_type={task_type}\n"
                f"decision={_json.dumps(decision, ensure_ascii=False)}\n"
                f"payload={_json.dumps(payload, ensure_ascii=False)}\n\n"
                "Return JSON with: divisions_required, platforms_targeted, content_types, "
                "kpi_targets, parallel_tasks, sequential_tasks"
            ),
            max_tokens=1024,
            json_mode=True,
        )
        ai_response = await gateway.complete(request)
        if ai_response.success and ai_response.parsed and not ai_response.used_fallback:
            ai_plan = ai_response.parsed
            existing_plan = state.get("execution_plan", {})
            ai_plan.setdefault("task_type", task_type)
            ai_plan.setdefault("priority", decision.get("priority", "high"))
            merged = {**existing_plan, **ai_plan}
            logger.info("[StrategicPlanning] AI-enhanced plan built | divisions=%s",
                       merged.get("divisions_required"))
            return {
                "execution_plan": merged,
                "pipeline_stage": "strategic_planning_complete",
            }
    except Exception as ai_exc:
        logger.debug("[StrategicPlanning] AI gateway skipped: %s", ai_exc)

    try:
        from sfc.divisions.base import DivisionInput
        from sfc.divisions.strategic_planning.service import StrategicPlanningService

        service = StrategicPlanningService()
        await service.initialize()
        result = await service.execute(DivisionInput(
            run_id=state.get("run_id", ""),
            task_type=task_type,
            payload={**payload, **decision},
            state_snapshot=dict(state),
        ))

        if result.success and result.data.get("execution_plan"):
            plan = result.data["execution_plan"]
            # Merge with any existing execution_plan keys (from planning_node)
            existing_plan = state.get("execution_plan", {})
            merged = {**existing_plan, **plan}
            logger.info("[StrategicPlanning] Plan built | divisions=%s", plan.get("divisions_required"))
            return {
                "execution_plan": merged,
                "pipeline_stage": "strategic_planning_complete",
            }
    except Exception as exc:
        logger.warning("[StrategicPlanning] Service failed, using minimal plan: %s", exc)

    # Minimal fallback plan
    return {
        "execution_plan": {
            "task_type": task_type,
            "priority": decision.get("priority", "high"),
            "divisions_required": decision.get("recommended_divisions", ["intelligence", "editorial"]),
            "platforms_targeted": ["tiktok", "x", "instagram_feed"],
            "content_types": ["article", "social_post"],
            "kpi_targets": {"reach": 50000},
            "parallel_tasks": ["intelligence"],
            "sequential_tasks": ["editorial", "creative", "governance", "publishing"],
        },
        "pipeline_stage": "strategic_planning_complete",
    }
