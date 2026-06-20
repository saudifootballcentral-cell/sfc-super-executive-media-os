"""TikTok Growth Specialist Persona."""
from __future__ import annotations

import logging
from typing import Any

from sfc.events.bus import get_event_bus
from sfc.personas.shared.types import PersonaCategory
from sfc.personas.media.shared.base import BaseMediaPersona
from sfc.personas.media.shared.models import ContentFormat, Platform, PlatformInsight
from sfc.personas.media.shared.events import TikTokOpportunityDetected

logger = logging.getLogger("sfc.personas.media.tiktok")


class TikTokPersona(BaseMediaPersona):
    PERSONA_ID = "MEDIA-TIKTOK-01"
    PERSONA_NAME = "TikTok Growth Specialist"
    PERSONA_CATEGORY = PersonaCategory.CREATIVE
    PERSONA_DESCRIPTION = (
        "Expert in TikTok virality, hooks, retention patterns, trending audio, "
        "and creator formats for Saudi football content."
    )
    PERSONA_CAPABILITIES = [
        "hook_creation",
        "viral_script_writing",
        "trend_detection",
        "retention_optimization",
        "audio_selection",
    ]
    PERSONA_PERFORMANCE_SCORE = 88.0
    PERSONA_PLATFORM = Platform.TIKTOK

    async def generate_insight(self, context: dict[str, Any]) -> PlatformInsight:
        topic = context.get("topic", "Saudi football")
        hook_style = context.get("hook_style", "question")
        get_event_bus().publish(
            TikTokOpportunityDetected(
                division="media_personas",
                run_id=context.get("run_id", ""),
                payload={"topic": topic, "hook_style": hook_style},
            )
        )
        return self._build_insight(
            context=context,
            content_format=ContentFormat.SHORT_VIDEO,
            title=f"TikTok Strategy — {topic}",
            summary=f"Viral TikTok content strategy for {topic} targeting Saudi football fans.",
            hook=f"Did you know {topic}? Here's what nobody is talking about...",
            recommendations=[
                "Post between 18:00-21:00 KSA time",
                "Use trending Saudi football audio",
                "Hook must work in first 2 seconds",
                "Add captions for 80% of viewers who watch muted",
            ],
            optimization_tips=[
                "Loop the ending back to the start",
                "Cut dead air ruthlessly",
                "Use 3-5 niche hashtags + 1 broad",
            ],
            virality_score=88.0,
            predicted_reach=250000,
            predicted_engagement_rate=8.5,
            predicted_ctr=5.2,
            tags=["tiktok", "viral", "short_form"],
        )

    async def generate_script(self, topic: str, duration_seconds: int = 30) -> dict[str, Any]:
        return {
            "topic": topic,
            "duration_seconds": duration_seconds,
            "hook": f"NOBODY is talking about this {topic} moment...",
            "act_1": f"Setup: The {topic} situation explained in 5 seconds",
            "act_2": "Build: The key insight or reveal",
            "act_3": "Payoff: The reaction / conclusion",
            "cta": "Follow for more Saudi football",
            "estimated_retention": "65%",
            "viral_probability": "high",
        }

    async def analyze_hook(self, hook_text: str) -> dict[str, Any]:
        curiosity_score = 85 if "?" in hook_text else 70
        urgency_words = ["nobody", "secret", "truth", "revealed"]
        has_urgency = any(w in hook_text.lower() for w in urgency_words)
        urgency_score = 75.0 if has_urgency else 60.0
        overall_score = round((curiosity_score + 80 + urgency_score) / 3, 1)
        return {
            "hook": hook_text,
            "curiosity_score": curiosity_score,
            "clarity_score": 80.0,
            "urgency_score": urgency_score,
            "overall_score": overall_score,
            "recommendation": (
                "Strong hook — proceed" if curiosity_score >= 80
                else "Strengthen with curiosity gap"
            ),
        }

    async def analyze(self, data: dict[str, Any]) -> dict[str, Any]:
        topic = data.get("topic", "football")
        return {
            "platform": "tiktok",
            "topic": topic,
            "recommended_format": "talking_head_with_broll",
            "ideal_length_seconds": 28,
            "hook_required": True,
            "trending_sounds": ["Saudi crowd chants", "Trending Arabic music"],
            "best_cta": "Follow for Saudi football daily",
        }
