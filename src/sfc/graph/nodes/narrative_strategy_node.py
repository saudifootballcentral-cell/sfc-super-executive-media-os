"""LangGraph node — Narrative Strategy."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("sfc.graph.nodes.narrative_strategy")


async def narrative_strategy_node(state: dict[str, Any]) -> dict[str, Any]:
    """Generate narrative strategy recommendations."""
    try:
        from sfc.narrative.modeling.service import get_narrative_modeling_service
        from sfc.narrative.strategy.service import get_strategy_engine
        strategy_engine = get_strategy_engine()
        modeling = get_narrative_modeling_service()

        all_profiles = modeling.get_profiles_by_type()
        strategy_reports = []
        for profile in all_profiles[:3]:
            report = await strategy_engine.recommend(profile)
            strategy_reports.append(report.to_dict())

        return {
            "narrative_strategy": {
                "reports": strategy_reports,
                "total": len(strategy_reports),
            },
            "pipeline_stage": "narrative_strategy",
        }
    except Exception as exc:
        logger.warning("narrative_strategy_node failed: %s", exc)
        warnings = list(state.get("warnings", []))
        warnings.append(f"narrative_strategy_node: {exc}")
        return {
            "narrative_strategy": {},
            "pipeline_stage": "narrative_strategy",
            "warnings": warnings,
        }
