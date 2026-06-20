"""X (Real-Time Conversation) Specialist Persona."""
from __future__ import annotations

import logging
from typing import Any

from sfc.events.bus import get_event_bus
from sfc.personas.shared.types import PersonaCategory
from sfc.personas.media.shared.base import BaseMediaPersona
from sfc.personas.media.shared.models import ContentFormat, Platform, PlatformInsight
from sfc.personas.media.shared.events import ThreadGenerated

logger = logging.getLogger("sfc.personas.media.x")


class XPersona(BaseMediaPersona):
    PERSONA_ID = "MEDIA-X-01"
    PERSONA_NAME = "Real-Time Conversation Specialist"
    PERSONA_CATEGORY = PersonaCategory.JOURNALISM
    PERSONA_DESCRIPTION = (
        "Expert in X (Twitter) threads, breaking news coverage, live match commentary, "
        "and real-time conversation strategy."
    )
    PERSONA_CAPABILITIES = [
        "thread_writing",
        "breaking_news_coverage",
        "live_match_commentary",
        "conversation_mapping",
        "trend_hijacking",
    ]
    PERSONA_PERFORMANCE_SCORE = 89.0
    PERSONA_PLATFORM = Platform.X

    async def generate_insight(self, context: dict[str, Any]) -> PlatformInsight:
        topic = context.get("topic", "match update")
        get_event_bus().publish(
            ThreadGenerated(
                division="media_personas",
                run_id=context.get("run_id", ""),
                payload={"topic": topic},
            )
        )
        return self._build_insight(
            context=context,
            content_format=ContentFormat.THREAD,
            title=f"X Strategy — {topic}",
            summary=f"Real-time X thread strategy for {topic} breaking news coverage.",
            hook=f"BREAKING: {topic} — here's everything you need to know \U0001f9f5\U0001f447",
            recommendations=[
                "First tweet must stand alone",
                "Thread optimal length: 8-12 tweets",
                "Post in live moments for reach spike",
                "Reply to own thread to boost",
            ],
            optimization_tips=[
                "Number tweets 1/ 2/ 3/",
                "Use media in tweet 3-4 for engagement",
                "End with question to drive replies",
            ],
            virality_score=85.0,
            predicted_reach=320000,
            predicted_engagement_rate=9.2,
            predicted_ctr=4.1,
        )

    async def generate_thread(
        self, topic: str, angle: str = "news", tweet_count: int = 8
    ) -> dict[str, Any]:
        tweets = []
        for i in range(tweet_count):
            if i == 0:
                text = f"BREAKING: {topic}"
            elif i < tweet_count - 1:
                text = f"Point {i}: Key insight about {topic}"
            else:
                text = "Follow @SFCOfficial for more Saudi football coverage"
            tweets.append({"n": i + 1, "text": text})
        return {
            "topic": topic,
            "angle": angle,
            "tweet_count": tweet_count,
            "tweets": tweets,
            "estimated_impressions": 250000,
            "optimal_time": "During live match or within 5 min of news breaking",
        }

    async def plan_live_coverage(self, match: str, duration_minutes: int = 105) -> dict[str, Any]:
        return {
            "match": match,
            "duration_min": duration_minutes,
            "coverage_plan": {
                "pre_match": "3 tweets: lineups, storylines, prediction",
                "kickoff": "Tweet every 5 min minimum",
                "key_moments": "Immediate tweet within 30 seconds",
                "halftime": "Summary thread 5-7 tweets",
                "full_time": "Result thread + reactions",
            },
            "tweet_volume_target": max(20, duration_minutes // 3),
        }

    async def analyze(self, data: dict[str, Any]) -> dict[str, Any]:
        topic = data.get("topic", "match")
        return {
            "platform": "x",
            "topic": topic,
            "content_type": "thread",
            "optimal_tweet_count": 10,
            "posting_window": "Live event or within 10 min of news",
            "engagement_driver": "Reply to your own thread",
        }
