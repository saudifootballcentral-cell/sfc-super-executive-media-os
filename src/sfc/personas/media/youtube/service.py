"""YouTube Growth Specialist Persona."""
from __future__ import annotations

import logging
from typing import Any

from sfc.events.bus import get_event_bus
from sfc.personas.shared.types import PersonaCategory
from sfc.personas.media.shared.base import BaseMediaPersona
from sfc.personas.media.shared.models import ContentFormat, Platform, PlatformInsight
from sfc.personas.media.shared.events import YouTubeOpportunityDetected

logger = logging.getLogger("sfc.personas.media.youtube")


class YouTubePersona(BaseMediaPersona):
    PERSONA_ID = "MEDIA-YOUTUBE-01"
    PERSONA_NAME = "YouTube Growth Specialist"
    PERSONA_CATEGORY = PersonaCategory.CREATIVE
    PERSONA_DESCRIPTION = (
        "Expert in YouTube long-form strategy, watch time optimization, CTR, "
        "retention curves, and recommendation algorithm."
    )
    PERSONA_CAPABILITIES = [
        "long_form_strategy",
        "watch_time_optimization",
        "ctr_optimization",
        "retention_analysis",
        "episode_structuring",
    ]
    PERSONA_PERFORMANCE_SCORE = 87.0
    PERSONA_PLATFORM = Platform.YOUTUBE

    async def generate_insight(self, context: dict[str, Any]) -> PlatformInsight:
        title = context.get("title", "Saudi Football Documentary")
        duration_min = context.get("duration_min", 20)
        get_event_bus().publish(
            YouTubeOpportunityDetected(
                division="media_personas",
                run_id=context.get("run_id", ""),
                payload={"title": title},
            )
        )
        return self._build_insight(
            context=context,
            content_format=ContentFormat.LONG_VIDEO,
            title=f"YouTube Strategy — {title}",
            summary=f"YouTube long-form strategy for '{title}' targeting Saudi football fans.",
            hook=f"In the next {duration_min} minutes, you'll understand why {title} changed everything",
            recommendations=[
                "Target 12-20 min for algorithm boost",
                "Place key revelation at 30% mark",
                "Use chapter markers",
                "Thumbnail must promise a clear outcome",
            ],
            optimization_tips=[
                "First 30 sec: restate the promise",
                "Use pattern interrupts every 3-4 min",
                "End screen with playlist CTA",
            ],
            virality_score=78.0,
            predicted_reach=95000,
            predicted_engagement_rate=5.8,
            predicted_ctr=7.2,
        )

    async def structure_episode(self, title: str, duration_min: int = 15) -> dict[str, Any]:
        return {
            "title": title,
            "duration_min": duration_min,
            "structure": {
                "0:00-0:30": "Hook: State the promise",
                "0:30-2:00": "Context: Why this matters",
                f"2:00-{duration_min - 3}:00": "Core content with chapter breaks every 4 min",
                f"{duration_min - 3}:00-{duration_min - 1}:00": "Payoff: The reveal/conclusion",
                f"{duration_min - 1}:00-{duration_min}:00": "CTA + subscribe ask",
            },
            "retention_target": "55%",
            "ctr_target": "7%",
        }

    async def optimize_for_watchtime(self, video_data: dict[str, Any]) -> dict[str, Any]:
        duration = video_data.get("duration_min", 15)
        target_watchtime = duration * 0.55
        return {
            "current_duration": duration,
            "target_watchtime_min": round(target_watchtime, 1),
            "retention_curve_target": "Hook strong, drop-off at 30% then plateau",
            "chapter_markers_recommended": max(3, duration // 4),
            "recommended_cuts": [
                "Remove intro music > 5 sec",
                "Cut filler phrases",
                "Add B-roll at every 60-second mark",
            ],
        }

    async def analyze(self, data: dict[str, Any]) -> dict[str, Any]:
        return {
            "platform": "youtube",
            "recommended_length_min": 15,
            "ctr_benchmark": "6-8%",
            "retention_benchmark": "50-60%",
            "upload_frequency": "2x per week",
            "best_day": "Saturday 10:00 KSA",
        }
