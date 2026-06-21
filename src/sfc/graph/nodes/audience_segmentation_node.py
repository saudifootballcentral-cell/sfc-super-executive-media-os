"""LangGraph node — Audience Segmentation."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("sfc.graph.nodes.audience_segmentation")


async def audience_segmentation_node(state: dict[str, Any]) -> dict[str, Any]:
    """Segment Saudi football audience into clusters."""
    try:
        from sfc.audience.segmentation.service import get_segmentation_engine
        engine = get_segmentation_engine()
        segments = await engine.segment()
        report = await engine.generate_report(segments)
        return {
            "audience_segments": report.to_dict(),
            "pipeline_stage": "audience_segmentation",
        }
    except Exception as exc:
        logger.warning("audience_segmentation_node failed: %s", exc)
        warnings = list(state.get("warnings", []))
        warnings.append(f"audience_segmentation_node: {exc}")
        return {
            "audience_segments": {},
            "pipeline_stage": "audience_segmentation",
            "warnings": warnings,
        }
