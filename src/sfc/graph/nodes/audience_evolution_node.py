"""LangGraph node — Audience Evolution."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("sfc.graph.nodes.audience_evolution")


async def audience_evolution_node(state: dict[str, Any]) -> dict[str, Any]:
    """Analyze audience evolution trends and forecast growth."""
    try:
        from sfc.audience.evolution.service import get_evolution_engine
        engine = get_evolution_engine()
        segments_data = state.get("audience_segments", {})
        segments = segments_data.get("segments", [])
        report = await engine.analyze_evolution(segments=segments or None)
        return {
            "audience_evolution": report.to_dict(),
            "pipeline_stage": "audience_evolution",
        }
    except Exception as exc:
        logger.warning("audience_evolution_node failed: %s", exc)
        warnings = list(state.get("warnings", []))
        warnings.append(f"audience_evolution_node: {exc}")
        return {
            "audience_evolution": {},
            "pipeline_stage": "audience_evolution",
            "warnings": warnings,
        }
