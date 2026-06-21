"""LangGraph node — Influence Network."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("sfc.graph.nodes.influence_network")


async def influence_network_node(state: dict[str, Any]) -> dict[str, Any]:
    """Map the Saudi football media influence network."""
    try:
        from sfc.influence.network.service import get_influence_network_engine
        engine = get_influence_network_engine()
        context = state.get("context", {})
        network = await engine.map_network(context=context)
        return {
            "influence_network": network.to_dict(),
            "pipeline_stage": "influence_network",
        }
    except Exception as exc:
        logger.warning("influence_network_node failed: %s", exc)
        warnings = list(state.get("warnings", []))
        warnings.append(f"influence_network_node: {exc}")
        return {
            "influence_network": {},
            "pipeline_stage": "influence_network",
            "warnings": warnings,
        }
