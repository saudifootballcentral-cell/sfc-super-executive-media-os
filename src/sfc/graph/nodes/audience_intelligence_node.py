"""Audience Intelligence Node — analyzes fan segments and engagement patterns."""

from __future__ import annotations

import logging
from typing import Any

from sfc.graph.state import SFCState

logger = logging.getLogger("sfc.graph.nodes.audience_intelligence_node")


async def audience_intelligence_node(state: SFCState) -> dict[str, Any]:
    """Node: audience_intelligence_node

    Analyzes Saudi football audience segments, preferences, and behavioral patterns.
    Identifies growth and retention opportunities.
    Results inform content strategy and platform targeting.
    """
    task_payload = state.get("task_payload", {})
    segment_types = task_payload.get("segment_types") or None

    logger.info("[AudienceIntelligenceNode] Analyzing audience segments")

    try:
        from sfc.social.audience.service import get_audience_service
        from sfc.social.audience.models import AudienceSegmentType

        service = get_audience_service()

        parsed_segments = None
        if segment_types:
            try:
                parsed_segments = [AudienceSegmentType(s) for s in segment_types]
            except (ValueError, KeyError):
                parsed_segments = None

        profile = await service.analyze(segment_types=parsed_segments)
        report = await service.generate_report(profile)
        audience_data = report.to_dict()

        logger.info(
            "[AudienceIntelligenceNode] Analysis complete | total=%d segments=%d growth=%.1f%%/mo",
            profile.total_audience,
            len(profile.segments),
            profile.growth_rate_monthly,
        )

        return {
            "audience_intelligence_data": audience_data,
            "pipeline_stage": "audience_intelligence_complete",
        }

    except Exception as exc:
        logger.error("[AudienceIntelligenceNode] Failed (non-fatal): %s", exc)
        return {
            "audience_intelligence_data": {"error": str(exc)},
            "pipeline_stage": "audience_intelligence_skipped",
            "warnings": [f"AUDIENCE_INTELLIGENCE_NODE_NON_FATAL: {exc}"],
        }
