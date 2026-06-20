"""Publishing Node — multi-platform content distribution.

Sequential — only approved content is published.
Package 2: PublishingDivision will replace the stub with real platform API calls.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from sfc.graph.state import SFCState

logger = logging.getLogger("sfc.node.publishing")

_PLATFORM_CONSTRAINTS: dict[str, dict[str, Any]] = {
    "tiktok":            {"max_chars": 150,   "hashtag_limit": 5,  "supports_video": True},
    "instagram_reels":   {"max_chars": 2200,  "hashtag_limit": 30, "supports_video": True},
    "instagram_stories": {"max_chars": 200,   "hashtag_limit": 10, "supports_video": True},
    "instagram_feed":    {"max_chars": 2200,  "hashtag_limit": 30, "supports_video": False},
    "youtube_shorts":    {"max_chars": 500,   "hashtag_limit": 15, "supports_video": True},
    "youtube":           {"max_chars": 5000,  "hashtag_limit": 500,"supports_video": True},
    "x":                 {"max_chars": 280,   "hashtag_limit": 2,  "supports_video": True},
    "telegram":          {"max_chars": 4096,  "hashtag_limit": 0,  "supports_video": True},
    "whatsapp":          {"max_chars": 1024,  "hashtag_limit": 0,  "supports_video": True},
    "website":           {"max_chars": 100000,"hashtag_limit": 0,  "supports_video": False},
    "newsletter":        {"max_chars": 50000, "hashtag_limit": 0,  "supports_video": False},
}


async def publishing_node(state: SFCState) -> dict[str, Any]:
    """Node: publishing

    Distributes approved content to all targeted platforms.
    Blocks on any unapproved content — only approved_content is published.

    Responsibilities:
    - Adapt content to platform constraints (character limits, formats)
    - Queue publish jobs per platform
    - Track publish IDs and timestamps

    Package 2: PublishingDivision will call real platform APIs.
    """
    approved_content = state.get("approved_content", [])
    rejected_count = len(state.get("rejected_content", []))
    revenue_signals = state.get("revenue_signals", [])

    logger.info(
        "[Publishing] %d approved | %d rejected | %d revenue signals",
        len(approved_content), rejected_count, len(revenue_signals),
    )

    if not approved_content:
        logger.warning("[Publishing] Nothing to publish — all content rejected or empty")
        return {
            "publish_queue": [],
            "publish_results": {
                "published_count": 0,
                "rejected_count": rejected_count,
                "status": "nothing_to_publish",
            },
            "pipeline_stage": "publishing_complete",
        }

    try:
        # Package 2: Call PublishingService with fallback to stub logic
        try:
            from sfc.divisions.publishing.service import PublishingService
            from sfc.divisions.base import DivisionInput
            service = PublishingService()
            await service.initialize()
            result = await service.execute(DivisionInput(
                run_id=state.get("run_id", ""),
                task_type=state.get("task_type", "news"),
                payload=state.get("task_payload", {}),
                state_snapshot=dict(state),
            ))
            if result.success:
                return {
                    "publish_queue": result.data.get("publish_queue", []),
                    "publish_results": result.data.get("publish_results", {}),
                    "pipeline_stage": "publishing_complete",
                }
        except Exception as svc_exc:
            logger.warning("[Publishing] Service call failed, using stub: %s", svc_exc)

        publish_queue: list[dict[str, Any]] = []
        platform_results: dict[str, list[dict[str, Any]]] = {}

        for content in approved_content:
            platforms = content.get("platforms", [])
            for platform in platforms:
                constraints = _PLATFORM_CONSTRAINTS.get(platform, {})
                body = content.get("body", "")
                max_chars = constraints.get("max_chars", 280)

                job = {
                    "job_id": str(uuid.uuid4()),
                    "content_id": content.get("content_id"),
                    "platform": platform,
                    "title": content.get("title", "")[:100],
                    "body_preview": body[:max_chars],
                    "char_count": min(len(body), max_chars),
                    "has_revenue_integration": _has_revenue_integration(platform, revenue_signals),
                    "status": "queued",
                    "queued_at": datetime.utcnow().isoformat(),
                }
                publish_queue.append(job)

                if platform not in platform_results:
                    platform_results[platform] = []
                platform_results[platform].append({
                    "job_id": job["job_id"],
                    "content_id": content.get("content_id"),
                    "status": "queued",
                })

        logger.info(
            "[Publishing] %d job(s) queued across %d platform(s)",
            len(publish_queue),
            len(platform_results),
        )

        return {
            "publish_queue": publish_queue,
            "publish_results": {
                "published_count": len(approved_content),
                "job_count": len(publish_queue),
                "rejected_count": rejected_count,
                "platform_results": platform_results,
                "status": "queued",
                "completed_at": datetime.utcnow().isoformat(),
            },
            "pipeline_stage": "publishing_complete",
        }

    except Exception as exc:
        logger.error("[Publishing] Failed: %s", exc)
        return {
            "publish_queue": [],
            "publish_results": {"status": "error", "error": str(exc)},
            "errors": [f"PUBLISHING: {exc}"],
        }


def _has_revenue_integration(platform: str, signals: list[dict[str, Any]]) -> bool:
    for signal in signals:
        if platform in signal.get("platforms", []):
            return True
    return False
