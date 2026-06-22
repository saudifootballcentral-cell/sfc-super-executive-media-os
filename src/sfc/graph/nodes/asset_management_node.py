"""LangGraph node — Creative Asset Management."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("sfc.graph.nodes.asset_management")


async def asset_management_node(state: dict[str, Any]) -> dict[str, Any]:
    """Register all produced assets into the asset registry."""
    try:
        from sfc.creative.assets.models import AssetStatus, AssetType
        from sfc.creative.assets.service import get_asset_management_service

        service = get_asset_management_service()

        for img in state.get("image_assets", []):
            service.register_asset(
                asset_type=AssetType.IMAGE,
                title=img.get("title", "Image"),
                platform=img.get("platform", ""),
                quality_score=img.get("brand_alignment_score", 0.0),
                brand_alignment_score=img.get("brand_alignment_score", 0.0),
                metadata={"image_format": img.get("image_format", ""), "variants": len(img.get("variants", []))},
            )

        for vid in state.get("video_assets", []):
            service.register_asset(
                asset_type=AssetType.VIDEO,
                title=vid.get("title", "Video"),
                platform=vid.get("platform", ""),
                file_url=vid.get("file_url", ""),
                quality_score=vid.get("brand_alignment_score", 0.0),
                brand_alignment_score=vid.get("brand_alignment_score", 0.0),
                metadata={"video_format": vid.get("video_format", ""), "duration_seconds": vid.get("duration_seconds", 0)},
            )

        for pkg in state.get("shorts_packages", []):
            service.register_asset(
                asset_type=AssetType.SHORTS_PACKAGE,
                title=pkg.get("title", "Shorts"),
                platform=pkg.get("platform", ""),
                metadata={"duration_seconds": pkg.get("duration_seconds", 0)},
            )

        for ep in state.get("podcast_episodes", []):
            service.register_asset(
                asset_type=AssetType.PODCAST_EPISODE,
                title=ep.get("episode_title", "Podcast"),
                platform="spotify",
                metadata={"podcast_type": ep.get("podcast_type", ""), "duration_minutes": ep.get("total_duration_minutes", 0)},
            )

        report = service.generate_registry_report()
        return {
            "asset_registry": report.to_dict(),
            "pipeline_stage": "asset_management",
        }
    except Exception as exc:
        logger.warning("asset_management_node failed: %s", exc)
        return {
            "asset_registry": {},
            "pipeline_stage": "asset_management",
            "warnings": [f"asset_management_node: {exc}"],
        }
