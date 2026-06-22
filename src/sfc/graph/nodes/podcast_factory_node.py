"""LangGraph node — AI Podcast Factory."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("sfc.graph.nodes.podcast_factory")


async def podcast_factory_node(state: dict[str, Any]) -> dict[str, Any]:
    """Generate podcast episode from narrative intelligence."""
    try:
        from sfc.creative.podcast.models import PodcastType
        from sfc.creative.podcast.service import get_podcast_factory_service

        service = get_podcast_factory_service()
        plan = state.get("production_plan", {})
        narrative = plan.get("narrative_context", "")
        trend = plan.get("trend_context", "")

        narratives: list[str] = []
        if narrative:
            narratives.append(narrative)
        if trend:
            narratives.append(trend)
        narratives = narratives or ["SFC Saudi football daily update"]

        episode = await service.generate_episode(
            episode_title=f"SFC Daily Show: {narratives[0][:40]}",
            podcast_type=PodcastType.DAILY_SHOW,
            narratives=narratives,
        )
        return {
            "podcast_episodes": [episode.to_dict()],
            "pipeline_stage": "podcast_factory",
        }
    except Exception as exc:
        logger.warning("podcast_factory_node failed: %s", exc)
        return {
            "podcast_episodes": [],
            "pipeline_stage": "podcast_factory",
            "warnings": [f"podcast_factory_node: {exc}"],
        }
