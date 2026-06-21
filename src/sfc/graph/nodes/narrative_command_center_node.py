"""LangGraph node — Narrative Command Center."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("sfc.graph.nodes.narrative_command_center")


async def narrative_command_center_node(state: dict[str, Any]) -> dict[str, Any]:
    """Run the full narrative intelligence pipeline via the command center."""
    try:
        from sfc.narrative.command_center import get_narrative_command_center
        center = get_narrative_command_center()
        context = state.get("context", {})
        dashboard = await center.run_full_intelligence(context=context)
        return {
            "narrative_command_center": dashboard,
            "pipeline_stage": "narrative_command_center",
        }
    except Exception as exc:
        logger.warning("narrative_command_center_node failed: %s", exc)
        warnings = list(state.get("warnings", []))
        warnings.append(f"narrative_command_center_node: {exc}")
        return {
            "narrative_command_center": {},
            "pipeline_stage": "narrative_command_center",
            "warnings": warnings,
        }
