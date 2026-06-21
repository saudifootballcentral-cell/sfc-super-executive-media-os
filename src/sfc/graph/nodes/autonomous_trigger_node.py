"""Autonomous Trigger Node — evaluates pipeline state for automatic workflow triggers."""

from __future__ import annotations

import logging
from typing import Any

from sfc.graph.state import SFCState

logger = logging.getLogger("sfc.graph.nodes.autonomous_trigger_node")


async def autonomous_trigger_node(state: SFCState) -> dict[str, Any]:
    """Node: autonomous_trigger_node

    Evaluates the completed pipeline state for trigger conditions.
    Fires autonomous trigger events when conditions are met.

    Sits after memory_update in the autonomous reporting pipeline.
    Does NOT modify content, governance decisions, or publishing.
    """
    task_type = state.get("task_type", "")

    logger.info("[AutonomousTrigger] Evaluating triggers | task=%s", task_type)

    try:
        from sfc.autonomous.trigger_engine import AutonomousTriggerEngine

        engine = AutonomousTriggerEngine()
        fired_events = await engine.evaluate_from_state(dict(state))

        trigger_report = engine.get_trigger_report()
        autonomous_triggers = [e.model_dump(mode="json") for e in fired_events]

        logger.info(
            "[AutonomousTrigger] %d trigger(s) fired | total_monitored=%d",
            len(fired_events),
            trigger_report.get("total_triggers", 0),
        )

        return {
            "autonomous_triggers": autonomous_triggers,
            "trigger_report": trigger_report,
            "pipeline_stage": "triggers_evaluated",
        }

    except Exception as exc:
        logger.error("[AutonomousTrigger] Failed (non-fatal): %s", exc)
        return {
            "autonomous_triggers": [],
            "pipeline_stage": "triggers_skipped",
            "warnings": [f"AUTONOMOUS_TRIGGER_NON_FATAL: {exc}"],
        }
