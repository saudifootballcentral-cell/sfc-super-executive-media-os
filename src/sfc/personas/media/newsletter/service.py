"""Audience Retention (Newsletter) Specialist Persona."""
from __future__ import annotations

import logging
from typing import Any

from sfc.events.bus import get_event_bus
from sfc.personas.shared.types import PersonaCategory
from sfc.personas.media.shared.base import BaseMediaPersona
from sfc.personas.media.shared.models import ContentFormat, Platform, PlatformInsight
from sfc.personas.media.shared.events import NewsletterGenerated

logger = logging.getLogger("sfc.personas.media.newsletter")


class NewsletterPersona(BaseMediaPersona):
    PERSONA_ID = "MEDIA-NEWSLETTER-01"
    PERSONA_NAME = "Audience Retention Specialist"
    PERSONA_CATEGORY = PersonaCategory.CREATIVE
    PERSONA_DESCRIPTION = (
        "Expert in email newsletter strategy, audience retention, open rate optimization, "
        "and direct relationship building for Saudi football fans."
    )
    PERSONA_CAPABILITIES = [
        "newsletter_planning",
        "email_sequence_design",
        "retention_optimization",
        "open_rate_improvement",
        "subscriber_growth",
    ]
    PERSONA_PERFORMANCE_SCORE = 81.0
    PERSONA_PLATFORM = Platform.NEWSLETTER

    async def generate_insight(self, context: dict[str, Any]) -> PlatformInsight:
        edition = context.get("edition", "Weekly Football Digest")
        get_event_bus().publish(
            NewsletterGenerated(
                division="media_personas",
                run_id=context.get("run_id", ""),
                payload={"edition": edition},
            )
        )
        return self._build_insight(
            context=context,
            content_format=ContentFormat.NEWSLETTER,
            title=f"Newsletter Strategy — {edition}",
            summary=f"Email newsletter strategy for '{edition}' to maximize open rates.",
            hook="Subject line that gets opened: 'You missed this week's biggest Saudi football story...'",
            recommendations=[
                "Subject line: curiosity gap or personalisation",
                "Preview text extends the subject line — don't waste it",
                "Lead with best story — email is skimmed not read",
                "One clear CTA per email",
            ],
            optimization_tips=[
                "Send Thu 07:00 or Fri 09:00 KSA for best open rates",
                "Segment: casual fans vs. hardcore fans",
                "Re-engagement: win back after 3 missed opens",
            ],
            virality_score=60.0,
            predicted_reach=25000,
            predicted_engagement_rate=28.5,
        )

    async def plan_edition(
        self, edition_name: str, top_stories: list[str]
    ) -> dict[str, Any]:
        subject_story = top_stories[0] if top_stories else "Saudi football update"
        extra_count = len(top_stories) - 1
        return {
            "edition": edition_name,
            "subject_line": f"\U0001f534 {subject_story} + {extra_count} more stories",
            "preview_text": "Your essential Saudi football briefing — 5 min read",
            "sections": [
                {
                    "name": "Top Story",
                    "content": top_stories[0] if top_stories else "Main story here",
                    "format": "300 word summary",
                },
                {
                    "name": "Quick Hits",
                    "content": "; ".join(top_stories[1:4]) if len(top_stories) > 1 else "More stories",
                    "format": "3-5 bullet points",
                },
                {
                    "name": "The Stat",
                    "content": "Key number of the week",
                    "format": "Single stat with context",
                },
                {
                    "name": "What to Watch",
                    "content": "Upcoming fixtures",
                    "format": "Fixture list with times",
                },
            ],
            "estimated_read_time_min": 4,
            "cta": "Share with a Saudi football fan",
        }

    async def design_retention_campaign(self, reason: str = "re-engagement") -> dict[str, Any]:
        return {
            "campaign_type": reason,
            "email_sequence": [
                {"email": 1, "subject": "We miss you — here's what you missed", "timing": "Day 0"},
                {"email": 2, "subject": "Saudi football's biggest moment this month", "timing": "Day 3"},
                {"email": 3, "subject": "Last chance — stay connected to Saudi football", "timing": "Day 7"},
            ],
            "expected_recovery_rate": "15-25%",
            "offer": "Exclusive Saudi football content not on social media",
        }

    async def analyze(self, data: dict[str, Any]) -> dict[str, Any]:
        return {
            "platform": "newsletter",
            "open_rate_benchmark": "22-28%",
            "ctr_benchmark": "3-5%",
            "optimal_frequency": "Weekly",
            "best_send_time": "Thursday 07:00 KSA",
        }
