"""LangGraph node — Narrative Lifecycle."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("sfc.graph.nodes.narrative_lifecycle")


async def narrative_lifecycle_node(state: dict[str, Any]) -> dict[str, Any]:
    """Analyze lifecycle stage of active narratives."""
    try:
        from sfc.narrative.lifecycle.service import get_lifecycle_engine
        engine = get_lifecycle_engine()
        narrative_map = state.get("narrative_models", {})
        profiles = narrative_map.get("profiles", [])
        narrative_ids = [p.get("profile_id", "") for p in profiles[:5]]
        if not narrative_ids:
            narrative_ids = ["default_narrative"]
        batch = await engine.batch_analyze(narrative_ids)
        return {
            "narrative_lifecycle": batch.to_dict(),
            "pipeline_stage": "narrative_lifecycle",
        }
    except Exception as exc:
        logger.warning("narrative_lifecycle_node failed: %s", exc)
        warnings = list(state.get("warnings", []))
        warnings.append(f"narrative_lifecycle_node: {exc}")
        return {
            "narrative_lifecycle": {},
            "pipeline_stage": "narrative_lifecycle",
            "warnings": warnings,
        }
