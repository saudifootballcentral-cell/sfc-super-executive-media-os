"""LangGraph node — Narrative Modeling."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("sfc.graph.nodes.narrative_modeling")


async def narrative_modeling_node(state: dict[str, Any]) -> dict[str, Any]:
    """Build narrative profiles and narrative map."""
    try:
        from sfc.narrative.modeling.service import get_narrative_modeling_service
        service = get_narrative_modeling_service()
        narrative_map = await service.build_narrative_map()
        return {
            "narrative_models": narrative_map.to_dict(),
            "pipeline_stage": "narrative_modeling",
        }
    except Exception as exc:
        logger.warning("narrative_modeling_node failed: %s", exc)
        warnings = list(state.get("warnings", []))
        warnings.append(f"narrative_modeling_node: {exc}")
        return {
            "narrative_models": {},
            "pipeline_stage": "narrative_modeling",
            "warnings": warnings,
        }
