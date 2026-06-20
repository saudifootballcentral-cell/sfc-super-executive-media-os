"""Search Growth (SEO) Specialist Persona."""
from __future__ import annotations

import logging
from typing import Any

from sfc.events.bus import get_event_bus
from sfc.personas.shared.types import PersonaCategory
from sfc.personas.media.shared.base import BaseMediaPersona
from sfc.personas.media.shared.models import ContentFormat, Platform, PlatformInsight
from sfc.personas.media.shared.events import SEORecommendationGenerated

logger = logging.getLogger("sfc.personas.media.seo")


class SEOPersona(BaseMediaPersona):
    PERSONA_ID = "MEDIA-SEO-01"
    PERSONA_NAME = "Search Growth Specialist"
    PERSONA_CATEGORY = PersonaCategory.ANALYTICS
    PERSONA_DESCRIPTION = (
        "Expert in SEO strategy for Saudi football content — keyword research, search intent, "
        "discoverability, and evergreen content planning."
    )
    PERSONA_CAPABILITIES = [
        "keyword_research",
        "search_intent_analysis",
        "content_optimization",
        "serp_strategy",
        "evergreen_planning",
    ]
    PERSONA_PERFORMANCE_SCORE = 83.0
    PERSONA_PLATFORM = Platform.SEO

    async def generate_insight(self, context: dict[str, Any]) -> PlatformInsight:
        topic = context.get("topic", "Saudi football")
        get_event_bus().publish(
            SEORecommendationGenerated(
                division="media_personas",
                run_id=context.get("run_id", ""),
                payload={"topic": topic},
            )
        )
        return self._build_insight(
            context=context,
            content_format=ContentFormat.ARTICLE,
            title=f"SEO Strategy — {topic}",
            summary=f"Search optimization strategy for {topic} content discoverability.",
            hook=(
                "The keyword that 10,000 Saudi football fans search every month "
                "— and we're not ranking for it."
            ),
            recommendations=[
                "Target long-tail Arabic keywords",
                "Match content to search intent: informational vs navigational",
                "Update evergreen content quarterly",
                "Internal linking between club and player profiles",
            ],
            optimization_tips=[
                "Title tag: primary keyword in first 3 words",
                "Meta description: include CTA",
                "Featured snippet: answer the question in first 50 words",
                "Image alt text in Arabic and English",
            ],
            virality_score=0.0,
            predicted_reach=80000,
            predicted_engagement_rate=2.5,
            predicted_ctr=4.2,
        )

    async def keyword_map(self, topic: str, intent: str = "informational") -> dict[str, Any]:
        return {
            "topic": topic,
            "intent": intent,
            "primary_keyword": f"{topic} Saudi Arabia",
            "secondary_keywords": [
                f"{topic} analysis",
                f"{topic} latest news",
                f"Saudi {topic} 2024",
            ],
            "arabic_keywords": [
                f"كرة القدم السعودية {topic[:10]}",
                f"الدوري السعودي {topic[:10]}",
            ],
            "monthly_search_volume_estimate": 8500,
            "competition": "medium",
            "recommended_content_type": (
                "comprehensive_guide" if intent == "informational" else "news_article"
            ),
        }

    async def optimize_article(self, title: str, word_count: int = 1200) -> dict[str, Any]:
        return {
            "title": title,
            "target_word_count": word_count,
            "structure": [
                "H1: Primary keyword + value proposition",
                "H2: What is [topic]?",
                "H2: Key analysis / facts",
                "H2: Impact on Saudi football",
                "H2: What's next?",
                "H2: FAQ section",
            ],
            "internal_links_target": 5,
            "external_links_target": 3,
            "image_count": max(2, word_count // 400),
            "schema_markup": "Article + FAQPage",
        }

    async def analyze(self, data: dict[str, Any]) -> dict[str, Any]:
        return {
            "platform": "seo",
            "target_search_engines": ["Google", "Google Arabic", "YouTube Search"],
            "content_types": [
                "Match previews",
                "Player profiles",
                "Transfer analysis",
                "League standings explainer",
            ],
            "update_frequency": "Match day = immediate; evergreen = quarterly",
        }
