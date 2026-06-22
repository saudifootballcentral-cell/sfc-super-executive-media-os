"""LangGraph node — AI Audio Factory."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("sfc.graph.nodes.audio_factory")


async def audio_factory_node(state: dict[str, Any]) -> dict[str, Any]:
    """Generate audio assets from production plan."""
    try:
        from sfc.creative.audio.models import AudioType, VoiceLanguage
        from sfc.creative.audio.service import get_audio_factory_service

        service = get_audio_factory_service()
        plan = state.get("production_plan", {})
        narrative = plan.get("narrative_context", "") or "SFC Saudi Football Daily Brief"

        audio_asset = await service.generate_audio(
            title=f"Audio Brief: {narrative[:50]}",
            audio_type=AudioType.NEWS_BRIEF,
            language=VoiceLanguage.ARABIC,
            platform="spotify",
        )
        return {
            "audio_assets": [audio_asset.to_dict()],
            "pipeline_stage": "audio_factory",
        }
    except Exception as exc:
        logger.warning("audio_factory_node failed: %s", exc)
        return {
            "audio_assets": [],
            "pipeline_stage": "audio_factory",
            "warnings": [f"audio_factory_node: {exc}"],
        }
