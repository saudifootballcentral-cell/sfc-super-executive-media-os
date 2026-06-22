"""LangGraph node — YouTube API Connector."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("sfc.graph.nodes.youtube_connector")


async def youtube_connector_node(state: dict[str, Any]) -> dict[str, Any]:
    """Publish YouTube-eligible content packages and read channel analytics."""
    try:
        from sfc.connectors.youtube.models import VideoUploadRequest, VideoCategory, VideoPrivacy
        from sfc.connectors.youtube.service import get_youtube_service

        service = get_youtube_service()
        content_packages = state.get("content_packages", [])

        yt_packages = [
            p for p in content_packages
            if p.get("package_type") in ("youtube_short", "youtube_video")
            and p.get("ready_to_publish", False)
        ]

        publish_results: list[dict[str, Any]] = []
        for pkg in yt_packages[:5]:
            is_short = pkg.get("package_type") == "youtube_short"
            req = VideoUploadRequest(
                title=pkg.get("title", "SFC Video"),
                description=pkg.get("description", ""),
                tags=pkg.get("hashtags", []),
                category=VideoCategory.SPORTS,
                privacy=VideoPrivacy.PUBLIC,
                file_url=pkg.get("media_assets", [{}])[0].get("file_url", "") if pkg.get("media_assets") else "",
                thumbnail_url=pkg.get("thumbnail_url", ""),
                is_short=is_short,
                language="ar",
            )
            if is_short:
                result = await service.upload_short(req)
            else:
                result = await service.upload_video(req)
            publish_results.append(result.to_dict())

        channel_metrics = await service.get_channel_metrics()
        report = await service.generate_report()

        return {
            "youtube_results": {
                "publish_results": publish_results,
                "channel_metrics": channel_metrics.to_dict(),
                "report": report.to_dict(),
                "observability": service.observability.to_dict(),
            },
            "pipeline_stage": "youtube_connector",
        }
    except Exception as exc:
        logger.warning("youtube_connector_node failed: %s", exc)
        return {
            "youtube_results": {},
            "pipeline_stage": "youtube_connector",
            "warnings": [f"youtube_connector_node: {exc}"],
        }
