"""Scheduler Node — exposes scheduler state and job management within the pipeline."""

from __future__ import annotations

import logging
from typing import Any

from sfc.graph.state import SFCState

logger = logging.getLogger("sfc.graph.nodes.scheduler_node")


async def scheduler_node(state: SFCState) -> dict[str, Any]:
    """Node: scheduler_node

    Provides scheduler state snapshot to the pipeline and evaluates any
    autonomous triggers based on the current pipeline context.

    Does NOT start the scheduler (lifecycle management is external).
    Does NOT modify governance or content approval.
    """
    task_type = state.get("task_type", "")
    run_id = state.get("run_id", "")

    logger.info("[SchedulerNode] Evaluating scheduler context | task=%s", task_type)

    try:
        from sfc.scheduler.engine import get_scheduler

        scheduler = get_scheduler()
        health = scheduler.get_health()

        fired_job_ids: list[str] = []
        try:
            context = {
                "analytics_report": state.get("analytics_report", {}),
                "revenue_signals": state.get("revenue_signals", []),
                "task_type": task_type,
                "run_id": run_id,
            }
            fired_job_ids = await scheduler.evaluate_triggers(context)
        except Exception as trigger_exc:
            logger.debug("[SchedulerNode] Trigger evaluation skipped: %s", trigger_exc)

        scheduler_state = {
            "health": health,
            "fired_trigger_count": len(fired_job_ids),
            "fired_job_ids": fired_job_ids,
            "is_running": health.get("is_running", False),
            "total_jobs": health.get("total_jobs", 0),
        }

        logger.info(
            "[SchedulerNode] Scheduler state captured | jobs=%d fired=%d",
            health.get("total_jobs", 0),
            len(fired_job_ids),
        )

        return {
            "scheduler_state": scheduler_state,
            "pipeline_stage": "scheduler_evaluated",
        }

    except Exception as exc:
        logger.error("[SchedulerNode] Failed (non-fatal): %s", exc)
        return {
            "scheduler_state": {"error": str(exc), "is_running": False},
            "pipeline_stage": "scheduler_skipped",
            "warnings": [f"SCHEDULER_NODE_NON_FATAL: {exc}"],
        }
