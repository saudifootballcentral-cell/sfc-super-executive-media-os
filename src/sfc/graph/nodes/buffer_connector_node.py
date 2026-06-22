"""LangGraph node — Buffer API Connector (multi-platform hub)."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("sfc.graph.nodes.buffer_connector")


async def buffer_connector_node(state: dict[str, Any]) -> dict[str, Any]:
    """Route content packages through Buffer to Instagram, Threads, Facebook, TikTok."""
    try:
        from sfc.connectors.buffer.service import get_buffer_service

        service = get_buffer_service()
        content_packages = state.get("content_packages", [])

        # Buffer handles non-YouTube, non-X packages
        buffer_packages = [
            p for p in content_packages
            if p.get("package_type") not in ("youtube_short", "youtube_video", "x_thread")
            and p.get("ready_to_publish", False)
        ]

        all_results: list[dict[str, Any]] = []
        for pkg in buffer_packages[:5]:
            results = await service.publish_content_package(pkg)
            all_results.extend([r.to_dict() for r in results])

        queue = await service.get_queue()
        report = await service.generate_report()

        return {
            "buffer_queue_state": {
                "publish_results": all_results,
                "queue": queue.to_dict(),
                "report": report.to_dict(),
                "observability": service.observability.to_dict(),
            },
            "pipeline_stage": "buffer_connector",
        }
    except Exception as exc:
        logger.warning("buffer_connector_node failed: %s", exc)
        return {
            "buffer_queue_state": {},
            "pipeline_stage": "buffer_connector",
            "warnings": [f"buffer_connector_node: {exc}"],
        }
