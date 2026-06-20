"""Short Form Video Specialist Persona."""
from __future__ import annotations

import logging
from typing import Any

from sfc.events.bus import get_event_bus
from sfc.personas.shared.types import PersonaCategory
from sfc.personas.media.shared.base import BaseMediaPersona
from sfc.personas.media.shared.models import ContentFormat, Platform, PlatformInsight

logger = logging.getLogger("sfc.personas.media.shorts")


class ShortsPersona(BaseMediaPersona):
    PERSONA_ID = "MEDIA-SHORTS-01"
    PERSONA_NAME = "Short Form Video Specialist"
    PERSONA_CATEGORY = PersonaCategory.CREATIVE
    PERSONA_DESCRIPTION = (
        "Expert in short-form video across TikTok, Reels, and YouTube Shorts — "
        "maximizing retention and value per second."
    )
    PERSONA_CAPABILITIES = [
        "short_script_writing",
        "retention_optimization",
        "cross_platform_adaptation",
        "compression_storytelling",
        "format_testing",
    ]
    PERSONA_PERFORMANCE_SCORE = 87.0
    PERSONA_PLATFORM = Platform.SHORTS

    async def generate_insight(self, context: dict[str, Any]) -> PlatformInsight:
        topic = context.get("topic", "football moment")
        return self._build_insight(
            context=context,
            content_format=ContentFormat.SHORT_VIDEO,
            title=f"Shorts Strategy — {topic}",
            summary=f"Short-form video strategy maximizing retention for {topic} content.",
            hook=f"You have 3 seconds to understand why {topic} matters.",
            recommendations=[
                "Max 60 seconds — ideally 28-35 sec",
                "No intro — start on the action",
                "Vertical 9:16 format mandatory",
                "Captions mandatory",
            ],
            optimization_tips=[
                "Loop potential: end connects to start",
                "Sound design critical — even without narration",
                "Surprise or reveal at 70% mark",
            ],
            virality_score=86.0,
            predicted_reach=200000,
            predicted_engagement_rate=7.8,
        )

    async def write_short_script(
        self, topic: str, duration_seconds: int = 30
    ) -> dict[str, Any]:
        return {
            "topic": topic,
            "duration_seconds": duration_seconds,
            "script": {
                "0-3s": f"HOOK: [Visual of key moment] — '{topic}' text overlay",
                "3-10s": "SETUP: Fast-cut context (no unnecessary words)",
                "10-25s": "CORE: The key insight/moment/stat",
                f"25-{duration_seconds}s": "PAYOFF + loop back to opening",
            },
            "narration_style": "Fast, punchy, no filler words",
            "b_roll_needed": True,
            "sound_on_required": False,
        }

    async def retention_analysis(self, script_data: dict[str, Any]) -> dict[str, Any]:
        script_val = script_data.get("script", "")
        words = len(script_val.split()) if isinstance(script_val, str) else 50
        pace_score = min(100.0, words * 2)
        return {
            "hook_strength": 85.0,
            "pacing_score": pace_score,
            "loop_potential": 70.0,
            "predicted_retention": f"{min(75, 55 + int(pace_score / 10))}%",
            "improvements": [
                "Tighten hook to under 5 words",
                "Add text overlay for silent viewers",
            ],
        }

    async def analyze(self, data: dict[str, Any]) -> dict[str, Any]:
        return {
            "platform": "shorts_universal",
            "max_duration_seconds": 60,
            "ideal_duration_seconds": 30,
            "hook_window_seconds": 3,
            "silent_viewing_rate": "80%",
            "caption_importance": "critical",
        }
