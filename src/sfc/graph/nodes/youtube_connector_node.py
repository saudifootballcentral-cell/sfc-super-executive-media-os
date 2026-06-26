"""LangGraph node — YouTube API Connector.

Dual-path: uses YouTubeService (direct) when YOUTUBE_CLIENT_ID is set,
otherwise falls back to Buffer (if BUFFER_ACCESS_TOKEN available).
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger("sfc.graph.nodes.youtube_connector")


async def youtube_connector_node(state: dict[str, Any]) -> dict[str, Any]:
    """Publish YouTube-eligible content packages and read channel analytics.

    Routing:
      - YOUTUBE_CLIENT_ID present → YouTubeService (direct)
      - BUFFER_ACCESS_TOKEN present → Buffer
      - Neither → skip publishing, still read channel analytics
    """
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
        route_used = "skipped"

        # --- Direct API path ---
        if os.environ.get("YOUTUBE_CLIENT_ID", ""):
            route_used = "direct"
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
                d = result.to_dict()
                d["route_used"] = "direct"
                publish_results.append(d)

        # --- Buffer fallback path ---
        elif os.environ.get("BUFFER_ACCESS_TOKEN", ""):
            route_used = "buffer"
            try:
                from sfc.connectors.buffer.service import get_buffer_service
                buf_service = get_buffer_service()
                for pkg in yt_packages[:5]:
                    buf_results = await buf_service.publish_content_package(pkg)
                    for r in buf_results:
                        d = r.to_dict()
                        d["route_used"] = "buffer"
                        publish_results.append(d)
            except Exception as buf_exc:
                logger.warning("[YouTube Connector] Buffer fallback failed: %s", buf_exc)

        else:
            # No real credentials — use mock service so pipeline keeps flowing
            route_used = "mock"
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
                d = result.to_dict()
                d["route_used"] = "mock"
                publish_results.append(d)

        channel_metrics = await service.get_channel_metrics()
        report = await service.generate_report()

        return {
            "youtube_results": {
                "publish_results": publish_results,
                "route_used": route_used,
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
