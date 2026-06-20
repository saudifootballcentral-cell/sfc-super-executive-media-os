"""Podcast Production Specialist Persona."""
from __future__ import annotations

import logging
from typing import Any

from sfc.events.bus import get_event_bus
from sfc.personas.shared.types import PersonaCategory
from sfc.personas.media.shared.base import BaseMediaPersona
from sfc.personas.media.shared.models import ContentFormat, Platform, PlatformInsight

logger = logging.getLogger("sfc.personas.media.podcast_producer")


class PodcastProducerPersona(BaseMediaPersona):
    PERSONA_ID = "MEDIA-PODCAST-PROD-01"
    PERSONA_NAME = "Podcast Production Specialist"
    PERSONA_CATEGORY = PersonaCategory.CREATIVE
    PERSONA_DESCRIPTION = (
        "Expert in podcast episode design, segment structure, audio flow, show architecture, "
        "and production quality for Saudi football content."
    )
    PERSONA_CAPABILITIES = [
        "episode_design",
        "segment_structuring",
        "show_architecture",
        "audio_flow_planning",
        "production_scheduling",
    ]
    PERSONA_PERFORMANCE_SCORE = 82.0
    PERSONA_PLATFORM = Platform.PODCAST

    async def generate_insight(self, context: dict[str, Any]) -> PlatformInsight:
        show_name = context.get("show_name", "SFC Podcast")
        return self._build_insight(
            context=context,
            content_format=ContentFormat.PODCAST_EPISODE,
            title=f"Podcast Production — {show_name}",
            summary=f"Episode design and production strategy for {show_name}.",
            hook=(
                f"A well-produced episode of {show_name} should feel effortless "
                "— here's the structure."
            ),
            recommendations=[
                "Consistent show structure builds listener habit",
                "Intro music max 10 seconds",
                "Each segment needs a clear opening and close",
                "Exit music signals subconsciously that value was delivered",
            ],
            optimization_tips=[
                "Chapter markers increase episode completion by 25%",
                "Cold open (0-60 sec) determines episode retention",
                "Segment transitions must be smooth — prep the listener",
            ],
            virality_score=65.0,
            predicted_reach=35000,
            predicted_engagement_rate=11.0,
        )

    async def design_episode_plan(
        self, episode_title: str, duration_min: int = 45
    ) -> dict[str, Any]:
        return {
            "episode": episode_title,
            "total_duration": duration_min,
            "segments": [
                {"name": "Cold Open", "duration_min": 1, "purpose": "Grab attention with best moment from episode"},
                {"name": "Intro + Theme Music", "duration_min": 1, "purpose": "Brand recognition"},
                {"name": "Main Story", "duration_min": 20, "purpose": "Core content"},
                {"name": "Analysis Segment", "duration_min": 15, "purpose": "Deep dive"},
                {"name": "Fan Voice / Q&A", "duration_min": 5, "purpose": "Community connection"},
                {"name": "Closing + Preview", "duration_min": 3, "purpose": "Retention and forward promise"},
            ],
            "production_notes": (
                "Record in order: main segment → outro → cold open (using best clip)"
            ),
        }

    async def create_show_structure(
        self, show_name: str, frequency: str = "weekly"
    ) -> dict[str, Any]:
        return {
            "show": show_name,
            "frequency": frequency,
            "episode_format": {
                "standard_length_min": 45,
                "segments": [
                    "Cold Open (1 min)",
                    "Intro (1 min)",
                    "Main Story (20 min)",
                    "Analysis (15 min)",
                    "Community Segment (5 min)",
                    "Outro (3 min)",
                ],
            },
            "branding_requirements": [
                "Consistent intro music",
                "Show jingle under 10 sec",
                "Branded transitions",
            ],
            "distribution": ["Spotify", "Apple Podcasts", "YouTube (full video)", "Anghami"],
        }

    async def analyze(self, data: dict[str, Any]) -> dict[str, Any]:
        return {
            "platform": "podcast_production",
            "quality_factors": ["Audio clarity", "Consistent levels", "Natural pacing"],
            "chapter_markers": "recommended",
            "video_podcast": "strongly_recommended_for_Saudi_market",
        }
