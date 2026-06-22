"""LangGraph node — AI Shorts Factory."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("sfc.graph.nodes.shorts_factory")


async def shorts_factory_node(state: dict[str, Any]) -> dict[str, Any]:
    """Generate short-form video packages."""
    try:
        from sfc.creative.shorts.models import ShortsPlatform
        from sfc.creative.shorts.service import get_shorts_factory_service

        service = get_shorts_factory_service()
        plan = state.get("production_plan", {})
        trend = plan.get("trend_context", "") or plan.get("narrative_context", "")
        title = f"SFC Shorts: {trend[:40]}" if trend else "SFC Saudi Football Shorts"

        packages: list[dict[str, Any]] = []
        for platform in [ShortsPlatform.YOUTUBE_SHORTS, ShortsPlatform.TIKTOK]:
            pkg = await service.generate_shorts_package(
                title=title,
                platform=platform,
                narrative=plan.get("narrative_context", ""),
            )
            packages.append(pkg.to_dict())

        return {
            "shorts_packages": packages,
            "pipeline_stage": "shorts_factory",
        }
    except Exception as exc:
        logger.warning("shorts_factory_node failed: %s", exc)
        return {
            "shorts_packages": [],
            "pipeline_stage": "shorts_factory",
            "warnings": [f"shorts_factory_node: {exc}"],
        }
