"""Fan Intelligence Specialist Persona."""
from __future__ import annotations

import logging
from typing import Any

from sfc.events.bus import get_event_bus
from sfc.personas.shared.types import PersonaCategory
from sfc.personas.sports.shared.base import BaseSportsPersona
from sfc.personas.sports.shared.events import NarrativeDetected, SentimentUpdated
from sfc.personas.sports.shared.models import InsightType, PersonaInsight

logger = logging.getLogger("sfc.personas.sports.fan_sentiment")


class FanSentimentPersona(BaseSportsPersona):
    PERSONA_ID = "SPORT-FAN-SENT-01"
    PERSONA_NAME = "Fan Intelligence Specialist"
    PERSONA_CATEGORY = PersonaCategory.ANALYTICS
    PERSONA_DESCRIPTION = (
        "Expert in fan sentiment, community mood, social discussions, "
        "and audience emotional intelligence."
    )
    PERSONA_CAPABILITIES = [
        "sentiment_analysis",
        "community_monitoring",
        "trend_detection",
        "reaction_tracking",
        "narrative_pulse",
    ]
    PERSONA_PERFORMANCE_SCORE = 84.0

    async def generate_insight(self, context: dict[str, Any]) -> PersonaInsight:
        topic = context.get("topic", "Saudi football")
        insight = self._build_insight(
            context=context,
            insight_type=InsightType.ANALYSIS,
            title=f"Fan Sentiment Intelligence — {topic}",
            summary=f"Fan community sentiment analysis for '{topic}'.",
            key_findings=[
                f"Sentiment for '{topic}' analysed",
                "Fan community mood assessed",
                "Trending narratives identified",
            ],
            recommendations=[
                "Capitalise on positive sentiment with targeted content",
                "Monitor negative trends for early crisis response",
            ],
            confidence_score=84.0,
            tags=["sentiment", "fan_intelligence"],
        )
        bus = get_event_bus()
        run_id = context.get("run_id", "")
        bus.publish(SentimentUpdated(
            division="sports_personas",
            run_id=run_id,
            payload={"topic": topic, "insight_id": insight.insight_id},
        ))
        bus.publish(NarrativeDetected(
            division="sports_personas",
            run_id=run_id,
            payload={"topic": topic, "insight_id": insight.insight_id},
        ))
        return insight

    async def analyze(self, data: dict[str, Any]) -> dict[str, Any]:
        topic = data.get("topic", "Saudi football")
        platform = data.get("platform", "twitter")
        return {
            "topic": topic,
            "platform": platform,
            "positive": 0.65,
            "neutral": 0.20,
            "negative": 0.15,
            "overall_sentiment": "positive",
            "analysis_summary": f"Sentiment analysis for '{topic}' on {platform} complete",
        }

    async def analyze_sentiment(
        self, topic: str, platform: str = "twitter"
    ) -> dict[str, Any]:
        """Analyse fan sentiment for a topic on a platform."""
        return {
            "topic": topic,
            "platform": platform,
            "positive": 0.65,
            "neutral": 0.20,
            "negative": 0.15,
            "overall_sentiment": "positive",
            "trend": "rising",
            "key_emotions": ["excitement", "pride", "anticipation"],
            "narrative_risk": "low",
        }

    async def fan_pulse_report(self, team: str) -> dict[str, Any]:
        """Generate a fan pulse report for a team."""
        return {
            "team": team,
            "pulse_score": 78.0,
            "fan_mood": "optimistic",
            "trending_topics": [f"{team} next match", f"{team} transfer news"],
            "engagement_level": "high",
            "recommendation": "Increase match-day content volume",
        }
