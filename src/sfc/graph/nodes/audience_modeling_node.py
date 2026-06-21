"""LangGraph node — Audience Modeling."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("sfc.graph.nodes.audience_modeling")


async def audience_modeling_node(state: dict[str, Any]) -> dict[str, Any]:
    """Build digital twin models for audience segments."""
    try:
        from sfc.audience.modeling.service import get_audience_modeling_engine
        engine = get_audience_modeling_engine()
        twins = await engine.build_models()
        report = await engine.generate_report(twins)
        return {
            "audience_models": report.to_dict(),
            "pipeline_stage": "audience_modeling",
        }
    except Exception as exc:
        logger.warning("audience_modeling_node failed: %s", exc)
        warnings = list(state.get("warnings", []))
        warnings.append(f"audience_modeling_node: {exc}")
        return {
            "audience_models": {},
            "pipeline_stage": "audience_modeling",
            "warnings": warnings,
        }
