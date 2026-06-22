"""LangGraph node — AI Image Factory."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("sfc.graph.nodes.image_factory")


async def image_factory_node(state: dict[str, Any]) -> dict[str, Any]:
    """Generate image assets from production plan."""
    try:
        from sfc.creative.image.models import ImageFormat
        from sfc.creative.image.service import get_image_factory_service

        service = get_image_factory_service()
        plan = state.get("production_plan", {})
        requests = plan.get("asset_requests", [])

        image_requests = [
            r for r in requests if r.get("content_format") == "image"
        ]
        if not image_requests:
            narrative = plan.get("narrative_context", "SFC Saudi Football")
            image_requests = [{"title": narrative or "SFC Match Day", "subject": ""}]

        assets: list[dict[str, Any]] = []
        for req in image_requests[:3]:
            asset = await service.generate_image(
                title=req.get("title", "SFC Image"),
                subject=req.get("subject", ""),
                image_format=ImageFormat.SOCIAL_CARD,
                platform=req.get("platform", "instagram"),
            )
            assets.append(asset.to_dict())

        return {
            "image_assets": assets,
            "pipeline_stage": "image_factory",
        }
    except Exception as exc:
        logger.warning("image_factory_node failed: %s", exc)
        return {
            "image_assets": [],
            "pipeline_stage": "image_factory",
            "warnings": [f"image_factory_node: {exc}"],
        }
