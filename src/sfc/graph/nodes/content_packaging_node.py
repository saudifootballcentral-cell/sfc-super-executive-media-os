"""LangGraph node — Content Packaging Engine."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("sfc.graph.nodes.content_packaging")


async def content_packaging_node(state: dict[str, Any]) -> dict[str, Any]:
    """Assemble platform-ready content packages from all produced assets."""
    try:
        from sfc.creative.packaging.models import PackageType
        from sfc.creative.packaging.service import get_content_packaging_service

        service = get_content_packaging_service()
        quality_reports = state.get("quality_reports", [])
        plan = state.get("production_plan", {})
        narrative = plan.get("narrative_context", "SFC Content")

        avg_quality = 0.0
        if quality_reports:
            avg_quality = sum(r.get("overall_score", 0) for r in quality_reports) / len(quality_reports)
        governance_cleared = avg_quality >= 70.0

        packages: list[dict[str, Any]] = []

        if state.get("video_assets"):
            vid = state["video_assets"][0]
            thumbnails = state.get("thumbnail_assets", [])
            thumbnail_url = ""
            if thumbnails:
                variants = thumbnails[0].get("variants", [])
                if variants:
                    thumbnail_url = variants[0].get("file_url", "")
            pkg = await service.create_package(
                package_type=PackageType.YOUTUBE_SHORT,
                title=vid.get("title", narrative),
                quality_score=avg_quality,
                governance_cleared=governance_cleared,
                thumbnail_url=thumbnail_url,
                media_assets=[vid],
            )
            packages.append(pkg.to_dict())

        if state.get("shorts_packages"):
            sp = state["shorts_packages"][0]
            pkg = await service.create_package(
                package_type=PackageType.TIKTOK,
                title=sp.get("title", narrative),
                caption=sp.get("caption", ""),
                hashtags=sp.get("hashtags", []),
                quality_score=avg_quality,
                governance_cleared=governance_cleared,
                media_assets=[sp],
            )
            packages.append(pkg.to_dict())

        if state.get("podcast_episodes"):
            ep = state["podcast_episodes"][0]
            pkg = await service.create_package(
                package_type=PackageType.PODCAST,
                title=ep.get("episode_title", narrative),
                description=ep.get("description", ""),
                quality_score=avg_quality,
                governance_cleared=governance_cleared,
                media_assets=[ep],
            )
            packages.append(pkg.to_dict())

        if not packages:
            pkg = await service.create_package(
                package_type=PackageType.INSTAGRAM,
                title=narrative[:60] or "SFC Content",
                quality_score=avg_quality,
                governance_cleared=governance_cleared,
            )
            packages.append(pkg.to_dict())

        return {
            "content_packages": packages,
            "pipeline_stage": "content_packaging",
        }
    except Exception as exc:
        logger.warning("content_packaging_node failed: %s", exc)
        return {
            "content_packages": [],
            "pipeline_stage": "content_packaging",
            "warnings": [f"content_packaging_node: {exc}"],
        }
