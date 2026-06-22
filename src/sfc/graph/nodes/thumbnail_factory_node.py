"""LangGraph node — AI Thumbnail Factory."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("sfc.graph.nodes.thumbnail_factory")


async def thumbnail_factory_node(state: dict[str, Any]) -> dict[str, Any]:
    """Generate thumbnail variants for video assets."""
    try:
        from sfc.creative.thumbnail.service import get_thumbnail_factory_service

        service = get_thumbnail_factory_service()
        video_assets = state.get("video_assets", [])
        plan = state.get("production_plan", {})

        titles_to_thumbnail = [v.get("title", "") for v in video_assets[:3]]
        if not titles_to_thumbnail:
            titles_to_thumbnail = [plan.get("narrative_context", "SFC Content") or "SFC Content"]

        assets: list[dict[str, Any]] = []
        for title in titles_to_thumbnail:
            asset = await service.generate_thumbnails(
                content_title=title,
                platform="youtube",
            )
            assets.append(asset.to_dict())

        return {
            "thumbnail_assets": assets,
            "pipeline_stage": "thumbnail_factory",
        }
    except Exception as exc:
        logger.warning("thumbnail_factory_node failed: %s", exc)
        return {
            "thumbnail_assets": [],
            "pipeline_stage": "thumbnail_factory",
            "warnings": [f"thumbnail_factory_node: {exc}"],
        }
