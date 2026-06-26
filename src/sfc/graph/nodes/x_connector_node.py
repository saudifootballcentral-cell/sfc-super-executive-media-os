"""LangGraph node — X API Connector (publishing + social intelligence feed).

Dual-path: uses XService (direct) when X_API_KEY is set, otherwise falls back to Buffer.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger("sfc.graph.nodes.x_connector")


async def x_connector_node(state: dict[str, Any]) -> dict[str, Any]:
    """Publish X-eligible content, monitor trends, and feed social intelligence.

    Routing:
      - X_API_KEY present → XService (direct)
      - BUFFER_ACCESS_TOKEN present → Buffer
      - Neither → skip publishing, still run trends/intelligence
    """
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
        route_used = "skipped"

        # --- Direct API path ---
        if os.environ.get("X_API_KEY", ""):
            route_used = "direct"
            for pkg in x_packages[:3]:
                caption = pkg.get("caption", "") or pkg.get("title", "")
                hashtags = pkg.get("hashtags", [])
                if hashtags:
                    caption = f"{caption}\n\n{' '.join(hashtags[:5])}"
                caption = caption[:280]
                post = await service.create_post(text=caption)
                result = post.to_dict()
                result["route_used"] = "direct"
                publish_results.append(result)

        # --- Buffer fallback path ---
        elif os.environ.get("BUFFER_ACCESS_TOKEN", ""):
            route_used = "buffer"
            try:
                from sfc.connectors.buffer.service import get_buffer_service
                buf_service = get_buffer_service()
                for pkg in x_packages[:3]:
                    buf_results = await buf_service.publish_content_package(pkg)
                    for r in buf_results:
                        d = r.to_dict()
                        d["route_used"] = "buffer"
                        publish_results.append(d)
            except Exception as buf_exc:
                logger.warning("[X Connector] Buffer fallback failed: %s", buf_exc)

        else:
            logger.info("[X Connector] No X or Buffer credentials — skipping publish")

        # Social intelligence feed (always runs)
        trends = await service.get_trending_topics()
        trend_dicts = [t.to_dict() for t in trends[:10]]

        keywords = state.get("social_intelligence_report", {}).get("monitor_keywords", [])
        kw_trends = await service.monitor_keywords(keywords[:5] if keywords else None)

        conversations = await service.search_conversations("SaudiFootball", max_results=5)

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
                "route_used": route_used,
                "social_intelligence": social_intelligence_update,
                "report": report.to_dict(),
                "observability": service.observability.to_dict(),
            },
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
