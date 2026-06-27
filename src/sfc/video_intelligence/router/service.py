"""Video Production Router — decides Mode A / B / C for each production request.

Decision logic:
  - If real footage is available AND AI video is configured → HYBRID (Mode C)
  - If real footage is available only → REAL_FOOTAGE (Mode A)
  - If AI video is configured only → AI_VIDEO (Mode B)
  - Neither available → AI_VIDEO with stub (fallback)
"""

from __future__ import annotations

import logging

from sfc.video_intelligence.router.models import ProductionMode, RouterDecision

logger = logging.getLogger("sfc.video_intelligence.router")

_singleton: "VideoProductionRouter | None" = None


def get_video_production_router() -> "VideoProductionRouter":
    global _singleton
    if _singleton is None:
        _singleton = VideoProductionRouter()
    return _singleton


class VideoProductionRouter:
    """Decides which production mode to use for a given request."""

    async def decide(
        self,
        topic: str,
        deadline_minutes: float = 60.0,
        quality_required: float = 70.0,
        footage_sources: list | None = None,
    ) -> RouterDecision:
        real_footage_available = bool(footage_sources)

        ai_video_available = self._check_ai_providers()

        if real_footage_available and ai_video_available:
            mode = ProductionMode.HYBRID
            reason = "Real footage available + AI providers configured — using hybrid pipeline"
            confidence = 0.9
        elif real_footage_available:
            mode = ProductionMode.REAL_FOOTAGE
            reason = "Real footage available — using Mode A real footage pipeline"
            confidence = 0.95
        elif ai_video_available:
            mode = ProductionMode.AI_VIDEO
            reason = "No footage available — generating with AI video providers"
            confidence = 0.85
        else:
            # No footage, no providers — use AI pipeline (will produce stub videos)
            mode = ProductionMode.AI_VIDEO
            reason = "No footage or AI providers available — AI pipeline with stub output"
            confidence = 0.5

        decision = RouterDecision(
            mode=mode,
            reason=reason,
            real_footage_available=real_footage_available,
            ai_video_available=ai_video_available,
            confidence=confidence,
        )

        logger.info(
            "[Router] topic=%s mode=%s confidence=%.2f reason=%s",
            topic, mode.value, confidence, reason,
        )
        return decision

    def _check_ai_providers(self) -> bool:
        """Return True if at least one AI video provider is configured."""
        import os
        return any([
            bool(os.environ.get("KLING_API_KEY")),
            bool(os.environ.get("RUNWAYML_API_SECRET")),
            bool(os.environ.get("LUMA_API_KEY")),
            bool(os.environ.get("PIKA_API_KEY")),
        ])

    def reset_for_test(self) -> None:
        pass
