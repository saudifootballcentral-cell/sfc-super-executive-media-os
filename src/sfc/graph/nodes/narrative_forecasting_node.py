"""LangGraph node — Narrative Forecasting."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("sfc.graph.nodes.narrative_forecasting")


async def narrative_forecasting_node(state: dict[str, Any]) -> dict[str, Any]:
    """Forecast narrative growth and reach across multiple horizons."""
    try:
        from sfc.narrative.forecasting.service import get_forecasting_engine
        engine = get_forecasting_engine()
        narrative_map = state.get("narrative_models", {})
        profiles = narrative_map.get("profiles", [])
        narrative_ids = [p.get("profile_id", "") for p in profiles[:5]]
        if not narrative_ids:
            narrative_ids = ["default_narrative"]
        bundle = await engine.forecast_bundle(narrative_ids)
        return {
            "narrative_forecast": bundle.to_dict(),
            "pipeline_stage": "narrative_forecasting",
        }
    except Exception as exc:
        logger.warning("narrative_forecasting_node failed: %s", exc)
        warnings = list(state.get("warnings", []))
        warnings.append(f"narrative_forecasting_node: {exc}")
        return {
            "narrative_forecast": {},
            "pipeline_stage": "narrative_forecasting",
            "warnings": warnings,
        }
