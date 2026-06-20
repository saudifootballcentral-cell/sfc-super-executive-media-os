"""Sports Show Host (Podcast Host) Persona."""
from __future__ import annotations

import logging
from typing import Any

from sfc.events.bus import get_event_bus
from sfc.personas.shared.types import PersonaCategory
from sfc.personas.media.shared.base import BaseMediaPersona
from sfc.personas.media.shared.models import ContentFormat, Platform, PlatformInsight
from sfc.personas.media.shared.events import PodcastGenerated

logger = logging.getLogger("sfc.personas.media.podcast_host")


class PodcastHostPersona(BaseMediaPersona):
    PERSONA_ID = "MEDIA-PODCAST-HOST-01"
    PERSONA_NAME = "Sports Show Host"
    PERSONA_CATEGORY = PersonaCategory.BROADCASTING
    PERSONA_DESCRIPTION = (
        "Expert sports podcast and show host — storytelling, interview technique, "
        "audience connection, and live commentary for Saudi football."
    )
    PERSONA_CAPABILITIES = [
        "show_hosting",
        "interview_technique",
        "live_commentary",
        "audience_connection",
        "narrative_storytelling",
    ]
    PERSONA_PERFORMANCE_SCORE = 85.0
    PERSONA_PLATFORM = Platform.PODCAST

    async def generate_insight(self, context: dict[str, Any]) -> PlatformInsight:
        episode_topic = context.get("topic", "SPL preview")
        get_event_bus().publish(
            PodcastGenerated(
                division="media_personas",
                run_id=context.get("run_id", ""),
                payload={"topic": episode_topic},
            )
        )
        return self._build_insight(
            context=context,
            content_format=ContentFormat.PODCAST_EPISODE,
            title=f"Podcast Host Strategy — {episode_topic}",
            summary=f"Sports show hosting strategy for '{episode_topic}' episode.",
            hook=(
                f"Welcome back. Today we need to talk about {episode_topic} "
                "— and it's more complicated than you think."
            ),
            recommendations=[
                "Open with a strong opinion or question",
                "Guest intro max 30 seconds",
                "Reference listener questions/feedback",
                "Close with a clear forward-looking statement",
            ],
            optimization_tips=[
                "40-55 min sweet spot for Saudi sports podcasts",
                "Energy peaks in first 10 min and after 30 min",
                "Strong episode title drives 70% of new listeners",
            ],
            virality_score=70.0,
            predicted_reach=45000,
            predicted_engagement_rate=14.5,
        )

    async def generate_discussion_guide(
        self,
        topic: str,
        guest: str = "",
        segment_count: int = 4,
    ) -> dict[str, Any]:
        segment_titles = ["Opening take", "Main story", "Analysis deep-dive", "Closing thoughts and prediction"]
        segment_durations = [5, 15, 12, 5]
        segments = []
        for i in range(min(segment_count, 4)):
            segments.append({
                "segment": i + 1,
                "title": segment_titles[i],
                "duration_min": segment_durations[i],
                "key_questions": [
                    f"Question {i + 1}a about {topic}",
                    f"Question {i + 1}b: wider context",
                ],
            })
        return {
            "topic": topic,
            "guest": guest or "Solo host",
            "segments": segments,
            "total_duration_min": 37,
            "opening_hook": (
                f"Hot take: {topic} changes everything we thought we knew about Saudi football"
            ),
        }

    async def plan_interview(self, guest_name: str, topic: str) -> dict[str, Any]:
        return {
            "guest": guest_name,
            "topic": topic,
            "warmup_questions": [
                "Tell us about your journey in Saudi football",
                f"What's the current situation with {topic}?",
            ],
            "challenge_questions": [
                "Critics say... how do you respond?",
                "What's the decision that keeps you up at night?",
            ],
            "closing_questions": [
                "What's your bold prediction for the season?",
                "One message for Saudi football fans?",
            ],
            "interview_duration_min": 30,
            "energy_management": "Build slowly, peak at mid-point, leave on a high",
        }

    async def analyze(self, data: dict[str, Any]) -> dict[str, Any]:
        return {
            "platform": "podcast",
            "optimal_length_min": 45,
            "release_frequency": "Weekly",
            "best_day": "Thursday (pre-weekend matches)",
            "listener_retention_target": "65%",
        }
