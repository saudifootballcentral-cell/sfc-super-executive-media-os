"""Autonomous Execution Node — coordinates all autonomous activity in the pipeline."""

from __future__ import annotations

import logging
from typing import Any

from sfc.graph.state import SFCState

logger = logging.getLogger("sfc.graph.nodes.autonomous_execution_node")


async def autonomous_execution_node(state: SFCState) -> dict[str, Any]:
    """Node: autonomous_execution_node

    Coordinates autonomous execution: dispatches trigger-fired requests,
    resolves priority conflicts, and returns execution status.

    Sits in the autonomous reporting pipeline between scheduler_node
    and reporting nodes.

    Does NOT modify governance decisions or content approval status.
    """
    task_type = state.get("task_type", "")
    scheduler_state = state.get("scheduler_state", {})
    autonomous_triggers = state.get("autonomous_triggers", [])

    logger.info(
        "[AutonomousExecution] Coordinating | task=%s triggers=%d",
        task_type,
        len(autonomous_triggers),
    )

    try:
        from sfc.autonomous.execution_manager import get_execution_manager, ExecutionRequest

        manager = get_execution_manager()
        submitted_ids: list[str] = []

        # Submit any fired trigger requests
        for trigger in autonomous_triggers:
            trigger_type = trigger.get("trigger_type", "unknown")
            request = ExecutionRequest(
                task_type=trigger.get("trigger_name", task_type),
                payload=trigger.get("context_snapshot", {}),
                priority="high",
                source=f"trigger:{trigger_type}",
            )
            req_id = await manager.submit(request)
            submitted_ids.append(req_id)

        execution_plan = manager.get_execution_plan()
        exec_report = manager.get_execution_report(limit=5)

        logger.info(
            "[AutonomousExecution] %d requests submitted | queued=%d running=%d",
            len(submitted_ids),
            execution_plan.get("queue_size", 0),
            execution_plan.get("running_count", 0),
        )

        return {
            "autonomous_execution_plan": {
                "submitted_request_ids": submitted_ids,
                "execution_plan": execution_plan,
                "recent_executions": exec_report.get("recent", [])[:3],
                "total_executions": exec_report.get("total_executions", 0),
                "success_rate_pct": exec_report.get("success_rate_pct", 100.0),
            },
            "pipeline_stage": "autonomous_execution_coordinated",
        }

    except Exception as exc:
        logger.error("[AutonomousExecution] Failed (non-fatal): %s", exc)
        return {
            "autonomous_execution_plan": {"error": str(exc)},
            "pipeline_stage": "autonomous_execution_skipped",
            "warnings": [f"AUTONOMOUS_EXECUTION_NON_FATAL: {exc}"],
        }
