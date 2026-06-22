"""LangGraph node — Production Quality Control."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("sfc.graph.nodes.quality_control")


async def quality_control_node(state: dict[str, Any]) -> dict[str, Any]:
    """Run quality checks on all produced creative assets."""
    try:
        from sfc.creative.quality.service import get_quality_control_service

        service = get_quality_control_service()

        assets_to_review: list[dict[str, Any]] = []

        for img in state.get("image_assets", []):
            assets_to_review.append({
                "asset_id": img.get("asset_id", ""),
                "asset_type": "image",
                "title": img.get("title", ""),
                "content": img.get("description", ""),
            })

        for vid in state.get("video_assets", []):
            assets_to_review.append({
                "asset_id": vid.get("asset_id", ""),
                "asset_type": "video",
                "title": vid.get("title", ""),
                "content": vid.get("prompt_used", ""),
            })

        for pkg in state.get("shorts_packages", []):
            assets_to_review.append({
                "asset_id": pkg.get("package_id", ""),
                "asset_type": "shorts_package",
                "title": pkg.get("title", ""),
                "content": pkg.get("caption", ""),
            })

        for ep in state.get("podcast_episodes", []):
            assets_to_review.append({
                "asset_id": ep.get("episode_id", ""),
                "asset_type": "podcast_episode",
                "title": ep.get("episode_title", ""),
                "content": ep.get("description", ""),
            })

        if not assets_to_review:
            assets_to_review.append({
                "asset_id": "placeholder",
                "asset_type": "placeholder",
                "title": "SFC Content",
                "content": "",
            })

        batch = await service.review_batch(assets_to_review)
        return {
            "quality_reports": [r.to_dict() for r in batch.reports],
            "pipeline_stage": "quality_control",
        }
    except Exception as exc:
        logger.warning("quality_control_node failed: %s", exc)
        return {
            "quality_reports": [],
            "pipeline_stage": "quality_control",
            "warnings": [f"quality_control_node: {exc}"],
        }
