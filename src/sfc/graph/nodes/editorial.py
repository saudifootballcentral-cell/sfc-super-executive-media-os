"""Editorial Node — content drafting based on verified intelligence.

Sequential — starts after intelligence_node completes.
Package 2: EditorialDivision will replace the stub logic.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from sfc.graph.state import SFCState

logger = logging.getLogger("sfc.node.editorial")


async def editorial_node(state: SFCState) -> dict[str, Any]:
    """Node: editorial

    Converts the intelligence report into content drafts.
    Each draft contains a title, body, target platforms, and initial scores.

    The confidence score is inherited from the intelligence report;
    governance will gate on confidence >= 85 and sources >= 2.

    Responsibilities:
    - News articles
    - Match analysis
    - Transfer stories
    - Video scripts
    - Trend pieces
    - Social posts

    Package 2: EditorialDivision will implement full AI-assisted writing.
    """
    task_type = state.get("task_type", "news")
    intel = state.get("intelligence_report", {})
    plan = state.get("execution_plan", {})
    payload = state.get("task_payload", {})
    verified_sources = state.get("verified_sources", [])

    logger.info("[Editorial] Drafting content | task=%s | content_types=%s",
                task_type, plan.get("content_types", []))

    try:
        # Package 2: Call EditorialService with fallback to stub logic
        try:
            from sfc.divisions.editorial.service import EditorialService
            from sfc.divisions.base import DivisionInput
            service = EditorialService()
            await service.initialize()
            result = await service.execute(DivisionInput(
                run_id=state.get("run_id", ""),
                task_type=task_type,
                payload=payload,
                state_snapshot=dict(state),
            ))
            if result.success and result.data.get("content_drafts"):
                return {
                    "content_drafts": result.data["content_drafts"],
                    "pipeline_stage": "editorial_complete",
                }
        except Exception as svc_exc:
            logger.warning("[Editorial] Service call failed, using stub: %s", svc_exc)

        content_types = plan.get("content_types", ["article"])
        platforms_targeted = plan.get("platforms_targeted", [])
        confidence = intel.get("confidence_score", 60.0)
        source_count = len(verified_sources)
        key_facts = intel.get("key_facts", [])
        is_rumor = intel.get("is_rumor", False)

        drafts: list[dict[str, Any]] = []

        for content_type in content_types:
            platforms_for_type = _select_platforms(content_type, platforms_targeted)
            draft = {
                "content_id": str(uuid.uuid4()),
                "title": _generate_title(content_type, payload, intel),
                "body": _generate_body(content_type, payload, intel, is_rumor),
                "content_type": content_type,
                "platforms": platforms_for_type,
                "status": "draft",
                "scores": {
                    "confidence_score": confidence,
                    "risk_score": max(0.0, 100.0 - confidence),
                    "source_count": source_count,
                    "brand_alignment_score": 85.0,
                },
                "sources": [s.get("name", "") for s in verified_sources],
                "is_rumor": is_rumor,
                "rumor_label": intel.get("rumor_label") if is_rumor else None,
                "key_facts": key_facts,
                "division": "editorial",
                "created_at": datetime.utcnow().isoformat(),
            }
            drafts.append(draft)

        logger.info("[Editorial] %d draft(s) produced | confidence=%.1f%%", len(drafts), confidence)

        return {
            "content_drafts": drafts,
            "pipeline_stage": "editorial_complete",
        }

    except Exception as exc:
        logger.error("[Editorial] Failed: %s", exc, exc_info=True)
        return {
            "content_drafts": [],
            "errors": [f"EDITORIAL: {exc}"],
        }


def _generate_title(content_type: str, payload: dict[str, Any], intel: dict[str, Any]) -> str:
    headline = payload.get("headline", "")
    if headline:
        return headline
    key_facts = intel.get("key_facts", [])
    if key_facts:
        return key_facts[0][:100]
    return f"Breaking: {payload.get('topic', 'Saudi Football News')}"


def _generate_body(
    content_type: str,
    payload: dict[str, Any],
    intel: dict[str, Any],
    is_rumor: bool,
) -> str:
    # TODO Package 2: Claude generates actual body
    body = payload.get("body", payload.get("details", ""))
    if is_rumor:
        body = f"[RUMOR — NOT CONFIRMED] {body}"
    return body or f"[Package 2: {content_type} body will be AI-generated here]"


def _select_platforms(content_type: str, available_platforms: list[str]) -> list[str]:
    video_types = {"highlight_clip", "live_update", "short_video", "teaser_clips",
                   "campaign_hero_video", "video_essay"}
    text_types = {"breaking_news_article", "long_form_analysis", "newsletter_edition",
                  "crisis_statement", "clarification_post"}
    social_types = {"social_post", "telegram_update", "analysis_thread", "carousel",
                    "graphic_announcement", "reaction_thread"}

    if content_type in video_types:
        video_platforms = {"tiktok", "instagram_reels", "youtube_shorts", "youtube", "instagram_stories"}
        return [p for p in available_platforms if p in video_platforms]
    if content_type in text_types:
        text_platforms = {"website", "newsletter", "telegram"}
        return [p for p in available_platforms if p in text_platforms]
    if content_type in social_types:
        social_platforms = {"x", "instagram_feed", "telegram", "whatsapp"}
        return [p for p in available_platforms if p in social_platforms]

    return available_platforms[:3]
