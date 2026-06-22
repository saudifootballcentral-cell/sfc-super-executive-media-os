"""LangGraph node — Analytics Sync (cross-platform metrics aggregation)."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("sfc.graph.nodes.analytics_sync")


async def analytics_sync_node(state: dict[str, Any]) -> dict[str, Any]:
    """Aggregate analytics from YouTube and X, update historical analytics store."""
    try:
        from sfc.connectors.analytics.service import get_analytics_sync_service

        service = get_analytics_sync_service()

        yt_results = state.get("youtube_results", {})
        x_results = state.get("x_results", {})

        # Extract published video/post IDs for targeted analytics pull
        yt_video_ids = [
            r.get("video_id", "")
            for r in yt_results.get("publish_results", [])
            if r.get("video_id")
        ]
        x_post_ids = [
            r.get("platform_post_id", "")
            for r in x_results.get("publish_results", [])
            if r.get("platform_post_id")
        ]

        report = await service.generate_sync_report(
            youtube_ids=yt_video_ids or None,
            x_ids=x_post_ids or None,
        )

        existing_historical = state.get("historical_analytics", {})
        updated_historical = {
            **existing_historical,
            "latest_sync": report.to_dict(),
            "total_views_cumulative": existing_historical.get("total_views_cumulative", 0)
            + report.total_views,
            "platforms_synced": report.platforms_synced,
        }

        return {
            "analytics_data": report.to_dict(),
            "historical_analytics": updated_historical,
            "pipeline_stage": "analytics_sync",
        }
    except Exception as exc:
        logger.warning("analytics_sync_node failed: %s", exc)
        return {
            "analytics_data": {},
            "pipeline_stage": "analytics_sync",
            "warnings": [f"analytics_sync_node: {exc}"],
        }
