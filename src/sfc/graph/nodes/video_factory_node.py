"""LangGraph node — AI Video Factory."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("sfc.graph.nodes.video_factory")


async def video_factory_node(state: dict[str, Any]) -> dict[str, Any]:
    """Generate video assets from production plan."""
    try:
        from sfc.creative.video.models import VideoFormat
        from sfc.creative.video.service import get_video_factory_service

        service = get_video_factory_service()
        plan = state.get("production_plan", {})
        requests = plan.get("asset_requests", [])

        video_requests = [
            r for r in requests
            if r.get("content_format") in ("short_video", "long_video")
        ]
        if not video_requests:
            narrative = plan.get("narrative_context", "SFC Highlights")
            video_requests = [{"title": narrative or "SFC Video", "platform": "youtube"}]

        assets: list[dict[str, Any]] = []
        for req in video_requests[:2]:
            asset = await service.generate_video(
                title=req.get("title", "SFC Video"),
                video_format=VideoFormat.SHORT,
                platform=req.get("platform", "youtube"),
                narrative=plan.get("narrative_context", ""),
            )
            assets.append(asset.to_dict())

        return {
            "video_assets": assets,
            "pipeline_stage": "video_factory",
        }
    except Exception as exc:
        logger.warning("video_factory_node failed: %s", exc)
        return {
            "video_assets": [],
            "pipeline_stage": "video_factory",
            "warnings": [f"video_factory_node: {exc}"],
        }
