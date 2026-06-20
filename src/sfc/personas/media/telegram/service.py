"""Telegram Community Specialist Persona."""
from __future__ import annotations

import logging
from typing import Any

from sfc.events.bus import get_event_bus
from sfc.personas.shared.types import PersonaCategory
from sfc.personas.media.shared.base import BaseMediaPersona
from sfc.personas.media.shared.models import ContentFormat, Platform, PlatformInsight

logger = logging.getLogger("sfc.personas.media.telegram")


class TelegramPersona(BaseMediaPersona):
    PERSONA_ID = "MEDIA-TELEGRAM-01"
    PERSONA_NAME = "Telegram Community Specialist"
    PERSONA_CATEGORY = PersonaCategory.CREATIVE
    PERSONA_DESCRIPTION = (
        "Expert in Telegram channel strategy — news distribution, community building, "
        "alert systems, and content engagement for Saudi football fans."
    )
    PERSONA_CAPABILITIES = [
        "telegram_channel_management",
        "community_building",
        "alert_system_design",
        "content_distribution",
        "engagement_planning",
    ]
    PERSONA_PERFORMANCE_SCORE = 82.0
    PERSONA_PLATFORM = Platform.TELEGRAM

    async def generate_insight(self, context: dict[str, Any]) -> PlatformInsight:
        channel_type = context.get("channel_type", "news")
        return self._build_insight(
            context=context,
            content_format=ContentFormat.ALERT,
            title=f"Telegram Strategy — {channel_type} channel",
            summary=f"Telegram channel strategy for {channel_type} distribution.",
            hook="[SFC TELEGRAM] Fast, accurate Saudi football news — delivered first.",
            recommendations=[
                "Channel posts: 5-8 per day maximum",
                "Breaking news: immediate, unformatted is fine",
                "Scheduled content: match previews, stats, polls",
                "Polls increase engagement 3x vs text posts",
            ],
            optimization_tips=[
                "Pin the most important daily post",
                "Use Telegram's media albums for match graphics",
                "Bot integration for automated stats/scores",
                "Channel description and link must be current",
            ],
            virality_score=74.0,
            predicted_reach=40000,
            predicted_engagement_rate=22.0,
        )

    async def create_channel_plan(
        self,
        channel_name: str,
        content_mix: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        default_mix: dict[str, Any] = {
            "breaking_news": 40,
            "analysis": 25,
            "graphics": 20,
            "polls": 10,
            "community": 5,
        }
        mix = content_mix or default_mix
        return {
            "channel": channel_name,
            "daily_posts_target": 6,
            "content_mix_pct": mix,
            "best_posting_times": ["08:00", "13:00", "18:00", "21:00"],
            "pinned_post_strategy": "Update daily with top story",
            "bot_features": ["Score updates", "Goal alerts", "Fixture reminders"],
        }

    async def generate_update(
        self, headline: str, detail: str = "", source: str = "SFC"
    ) -> dict[str, Any]:
        text = f"\U0001f534 **{headline}**\n\n{detail}\n\n\U0001f4cc Source: {source}"
        return {
            "text": text,
            "has_media": bool(detail),
            "format": "channel_post",
            "instant_view": True,
            "schedule": "Immediate for breaking, scheduled for planned",
            "char_count": len(headline) + len(detail) + 30,
        }

    async def analyze(self, data: dict[str, Any]) -> dict[str, Any]:
        return {
            "platform": "telegram",
            "advantages": ["No algorithm", "Instant delivery", "Rich media support"],
            "optimal_posts_per_day": 6,
            "engagement_driver": "Polls and exclusive content",
        }
