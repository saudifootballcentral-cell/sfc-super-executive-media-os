"""WhatsApp Channel Specialist Persona."""
from __future__ import annotations

import logging
from typing import Any

from sfc.events.bus import get_event_bus
from sfc.personas.shared.types import PersonaCategory
from sfc.personas.media.shared.base import BaseMediaPersona
from sfc.personas.media.shared.models import ContentFormat, Platform, PlatformInsight

logger = logging.getLogger("sfc.personas.media.whatsapp")


class WhatsAppPersona(BaseMediaPersona):
    PERSONA_ID = "MEDIA-WHATSAPP-01"
    PERSONA_NAME = "WhatsApp Channel Specialist"
    PERSONA_CATEGORY = PersonaCategory.CREATIVE
    PERSONA_DESCRIPTION = (
        "Expert in WhatsApp Channel strategy for Saudi football — instant notifications, "
        "digest content, retention, and fan engagement."
    )
    PERSONA_CAPABILITIES = [
        "whatsapp_content_planning",
        "notification_design",
        "digest_creation",
        "retention_optimization",
        "engagement_maximization",
    ]
    PERSONA_PERFORMANCE_SCORE = 84.0
    PERSONA_PLATFORM = Platform.WHATSAPP

    async def generate_insight(self, context: dict[str, Any]) -> PlatformInsight:
        update_type = context.get("update_type", "match alert")
        headline = context.get("headline", "Breaking Saudi football news")
        return self._build_insight(
            context=context,
            content_format=ContentFormat.ALERT,
            title=f"WhatsApp Strategy — {update_type}",
            summary=f"WhatsApp Channel content strategy for {update_type} updates.",
            hook=f"[ALERT] ⚽ {headline}",
            recommendations=[
                "Message max 280 characters for mobile readability",
                "Use emojis sparingly — they aid scanning",
                "One link per message maximum",
                "Breaking news: send immediately, no delay",
            ],
            optimization_tips=[
                "Morning digest: 08:00 KSA",
                "Match alerts: real-time",
                "Pin most important channel updates",
                "Weekly recap: Sunday 20:00",
            ],
            virality_score=78.0,
            predicted_reach=55000,
            predicted_engagement_rate=35.0,
        )

    async def create_match_alert(
        self,
        home: str,
        away: str,
        time_kat: str,
        competition: str = "SPL",
    ) -> dict[str, Any]:
        body = f"⚽ TONIGHT\n\U0001f19f {home} vs {away}\n\U0001f550 {time_kat} (KSA)\n\U0001f3c6 {competition}"
        message = f"{body}\n\n\U0001f4f1 Full coverage on our channels"
        return {
            "message": message,
            "character_count": len(body),
            "send_timing": "3 hours before kickoff + reminder 30 min before",
            "include_link": True,
            "format": "multi_line",
        }

    async def design_daily_digest(
        self, date: str, stories: list[str]
    ) -> dict[str, Any]:
        story_bullets = [f"• {s}" for s in stories[:5]]
        return {
            "date": date,
            "title": f"\U0001f4f0 Saudi Football Daily — {date}",
            "stories": story_bullets,
            "footer": "Stay connected: [link]",
            "character_estimate": sum(len(s) + 3 for s in stories[:5]) + 60,
            "send_time": "08:00 KSA",
            "format": "daily_briefing",
        }

    async def analyze(self, data: dict[str, Any]) -> dict[str, Any]:
        return {
            "platform": "whatsapp",
            "open_rate": "98% (push notification)",
            "best_content": ["Match alerts", "Goal updates", "Breaking transfers"],
            "frequency": "Max 3 messages per day",
            "format": "Short, scannable, emoji-assisted",
        }
