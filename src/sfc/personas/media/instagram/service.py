"""Instagram Growth Specialist Persona."""
from __future__ import annotations

import logging
from typing import Any

from sfc.events.bus import get_event_bus
from sfc.personas.shared.types import PersonaCategory
from sfc.personas.media.shared.base import BaseMediaPersona
from sfc.personas.media.shared.models import ContentFormat, Platform, PlatformInsight
from sfc.personas.media.shared.events import InstagramOpportunityDetected

logger = logging.getLogger("sfc.personas.media.instagram")


class InstagramPersona(BaseMediaPersona):
    PERSONA_ID = "MEDIA-INSTAGRAM-01"
    PERSONA_NAME = "Instagram Growth Specialist"
    PERSONA_CATEGORY = PersonaCategory.CREATIVE
    PERSONA_DESCRIPTION = (
        "Expert in Instagram Reels, Stories, Carousels, saves/shares optimization, "
        "and audience growth for Saudi football."
    )
    PERSONA_CAPABILITIES = [
        "reels_creation",
        "story_design",
        "carousel_planning",
        "engagement_optimization",
        "saves_maximization",
    ]
    PERSONA_PERFORMANCE_SCORE = 86.0
    PERSONA_PLATFORM = Platform.INSTAGRAM

    async def generate_insight(self, context: dict[str, Any]) -> PlatformInsight:
        topic = context.get("topic", "match day")
        get_event_bus().publish(
            InstagramOpportunityDetected(
                division="media_personas",
                run_id=context.get("run_id", ""),
                payload={"topic": topic},
            )
        )
        return self._build_insight(
            context=context,
            content_format=ContentFormat.REEL,
            title=f"Instagram Strategy — {topic}",
            summary=f"Instagram Reels and carousel strategy for {topic} content.",
            hook=f"Save this if you're a Saudi football fan \U0001f44a — {topic} breakdown",
            recommendations=[
                "Optimize first frame for saves",
                "Use carousel for tactical breakdowns",
                "Post Stories 2h before Reels for warmup",
                "Add location tags for Saudi cities",
            ],
            optimization_tips=[
                "End Reels with 'save this for later'",
                "Carousel last slide = CTA",
                "Stories: poll in slide 2",
            ],
            virality_score=82.0,
            predicted_reach=180000,
            predicted_engagement_rate=6.2,
            predicted_ctr=3.8,
        )

    async def plan_reels(self, topic: str, count: int = 3) -> dict[str, Any]:
        return {
            "topic": topic,
            "reels_planned": count,
            "hooks": [f"Reel {i + 1}: {topic} — angle {i + 1}" for i in range(count)],
            "posting_schedule": ["Monday 19:00", "Wednesday 18:30", "Friday 20:00"],
            "goal": "saves_and_shares",
            "estimated_total_reach": count * 120000,
        }

    async def design_carousel(self, topic: str, slides: int = 7) -> dict[str, Any]:
        return {
            "topic": topic,
            "slides": slides,
            "structure": {
                "slide_1": f"Hook: {topic} — the truth",
                "slide_2": "The problem / context",
                "slides_3_to_N-1": "Value content (stats, insight, story)",
                f"slide_{slides}": "CTA: Save + Follow",
            },
            "optimal_slide_count": 7,
            "engagement_prediction": "high_saves",
        }

    async def analyze(self, data: dict[str, Any]) -> dict[str, Any]:
        return {
            "platform": "instagram",
            "topic": data.get("topic", "football"),
            "recommended_format": "reel_plus_carousel",
            "ideal_reel_length_seconds": 22,
            "carousel_slides": 7,
            "save_rate_target": "8%",
            "best_time": "Fri-Sat 19:00-21:00 KSA",
        }
