"""Long Form Storytelling (Documentary) Specialist Persona."""
from __future__ import annotations

import logging
from typing import Any

from sfc.events.bus import get_event_bus
from sfc.personas.shared.types import PersonaCategory
from sfc.personas.media.shared.base import BaseMediaPersona
from sfc.personas.media.shared.models import ContentFormat, Platform, PlatformInsight

logger = logging.getLogger("sfc.personas.media.documentary")


class DocumentaryPersona(BaseMediaPersona):
    PERSONA_ID = "MEDIA-DOC-01"
    PERSONA_NAME = "Long Form Storytelling Specialist"
    PERSONA_CATEGORY = PersonaCategory.CREATIVE
    PERSONA_DESCRIPTION = (
        "Expert in documentary storytelling, narrative arcs, emotional journeys, "
        "historical context, and legacy content for Saudi football."
    )
    PERSONA_CAPABILITIES = [
        "narrative_arc_design",
        "character_development",
        "historical_research",
        "emotional_storytelling",
        "series_planning",
    ]
    PERSONA_PERFORMANCE_SCORE = 84.0
    PERSONA_PLATFORM = Platform.DOCUMENTARY

    async def generate_insight(self, context: dict[str, Any]) -> PlatformInsight:
        title = context.get("title", "Saudi Football Story")
        key_moment = context.get("key_moment", "2022")
        return self._build_insight(
            context=context,
            content_format=ContentFormat.LONG_VIDEO,
            title=f"Documentary Strategy — {title}",
            summary=f"Long-form documentary storytelling strategy for '{title}'.",
            hook=f"Every great story has a turning point. For Saudi football, it was {key_moment}.",
            recommendations=[
                "Structure in 3 acts minimum",
                "Open with the emotional payoff, then go back",
                "Use real voices — player interviews, fan moments",
                "Music must match the emotional journey",
            ],
            optimization_tips=[
                "Cold open in first 90 seconds or lose the viewer",
                "Chapter titles increase perceived value",
                "End with a question that demands a sequel",
            ],
            virality_score=72.0,
            predicted_reach=120000,
            predicted_engagement_rate=12.5,
        )

    async def create_outline(
        self,
        title: str,
        episode_count: int = 1,
        duration_min_per_episode: int = 25,
    ) -> dict[str, Any]:
        d = duration_min_per_episode
        return {
            "title": title,
            "episodes": episode_count,
            "duration_per_ep": duration_min_per_episode,
            "structure": {
                "act_1_setup": f"0-{d // 3} min: Establish world, characters, stakes",
                "act_2_conflict": f"{d // 3}-{2 * d // 3} min: The challenge/journey",
                "act_3_resolution": f"{2 * d // 3}-{d} min: Resolution + legacy",
            },
            "narrative_devices": [
                "Opening cold scene",
                "Interview cutaways",
                "Archival footage moments",
                "Chapter title cards",
            ],
        }

    async def develop_character(
        self, subject: str, role: str = "protagonist"
    ) -> dict[str, Any]:
        return {
            "subject": subject,
            "role": role,
            "story_arc": f"The rise of {subject} in Saudi football",
            "key_moments": [
                f"{subject}'s debut",
                "First major achievement",
                "Defining challenge",
                "Legacy moment",
            ],
            "emotional_core": "perseverance and national pride",
            "interview_questions": [
                "What drove you to succeed?",
                "What does Saudi football mean to you?",
                "What would you tell the next generation?",
            ],
        }

    async def analyze(self, data: dict[str, Any]) -> dict[str, Any]:
        return {
            "platform": "documentary",
            "optimal_length_min": 25,
            "series_potential": True,
            "audience_type": "engaged_fan",
            "distribution": ["YouTube", "Saudi streaming platforms"],
            "production_complexity": "high",
        }
