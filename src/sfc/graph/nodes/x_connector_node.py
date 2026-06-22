"""LangGraph node — X API Connector (publishing + social intelligence feed)."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("sfc.graph.nodes.x_connector")


async def x_connector_node(state: dict[str, Any]) -> dict[str, Any]:
    """Publish X-eligible content, monitor trends, and feed social intelligence."""
    try:
        from sfc.connectors.x.service import get_x_service

        service = get_x_service()
        content_packages = state.get("content_packages", [])

        x_packages = [
            p for p in content_packages
            if p.get("package_type") == "x_thread"
            and p.get("ready_to_publish", False)
        ]

        publish_results: list[dict[str, Any]] = []
        for pkg in x_packages[:3]:
            caption = pkg.get("caption", "") or pkg.get("title", "")
            hashtags = pkg.get("hashtags", [])
            if hashtags:
                caption = f"{caption}\n\n{' '.join(hashtags[:5])}"
            caption = caption[:280]
            post = await service.create_post(text=caption)
            publish_results.append(post.to_dict())

        # Social intelligence feed (runs every cycle regardless of publishing)
        trends = await service.get_trending_topics()
        trend_dicts = [t.to_dict() for t in trends[:10]]

        keywords = state.get("social_intelligence_report", {}).get("monitor_keywords", [])
        kw_trends = await service.monitor_keywords(keywords[:5] if keywords else None)

        conversations = await service.search_conversations("SaudiFootball", max_results=5)

        # Feed into 8B-compatible state keys
        social_intelligence_update = {
            "trending_topics": trend_dicts,
            "keyword_trends": [t.to_dict() for t in kw_trends],
            "conversations_detected": len(conversations),
            "top_trend": trends[0].term if trends else "",
            "top_trend_volume": trends[0].tweet_volume if trends else 0,
        }

        report = await service.generate_report()

        return {
            "x_results": {
                "publish_results": publish_results,
                "social_intelligence": social_intelligence_update,
                "report": report.to_dict(),
                "observability": service.observability.to_dict(),
            },
            # Also write back to trend_radar_data for 8B/8C feed
            "trend_radar_data": {
                **state.get("trend_radar_data", {}),
                "live_trends": trend_dicts,
                "top_trend": trends[0].term if trends else "",
            },
            "pipeline_stage": "x_connector",
        }
    except Exception as exc:
        logger.warning("x_connector_node failed: %s", exc)
        return {
            "x_results": {},
            "pipeline_stage": "x_connector",
            "warnings": [f"x_connector_node: {exc}"],
        }
