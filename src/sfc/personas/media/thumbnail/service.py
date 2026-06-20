"""Thumbnail Optimization Specialist Persona."""
from __future__ import annotations

import logging
from typing import Any

from sfc.events.bus import get_event_bus
from sfc.personas.shared.types import PersonaCategory
from sfc.personas.media.shared.base import BaseMediaPersona
from sfc.personas.media.shared.models import ContentFormat, Platform, PlatformInsight
from sfc.personas.media.shared.events import ThumbnailCreated

logger = logging.getLogger("sfc.personas.media.thumbnail")


class ThumbnailPersona(BaseMediaPersona):
    PERSONA_ID = "MEDIA-THUMB-01"
    PERSONA_NAME = "Thumbnail Optimization Specialist"
    PERSONA_CATEGORY = PersonaCategory.CREATIVE
    PERSONA_DESCRIPTION = (
        "Expert in thumbnail CTR optimization, visual hierarchy, emotional triggers, "
        "and click-earning design for football content."
    )
    PERSONA_CAPABILITIES = [
        "ctr_optimization",
        "visual_hierarchy_design",
        "emotion_triggering",
        "contrast_optimization",
        "ab_testing_design",
    ]
    PERSONA_PERFORMANCE_SCORE = 86.0
    PERSONA_PLATFORM = Platform.THUMBNAIL

    async def generate_insight(self, context: dict[str, Any]) -> PlatformInsight:
        title = context.get("title", "Video")
        get_event_bus().publish(
            ThumbnailCreated(
                division="media_personas",
                run_id=context.get("run_id", ""),
                payload={"title": title},
            )
        )
        return self._build_insight(
            context=context,
            content_format=ContentFormat.GRAPHIC,
            title=f"Thumbnail Strategy — {title}",
            summary=f"CTR-optimized thumbnail concept for '{title}'.",
            hook=f"[THUMBNAIL] Earn the click: {title}",
            recommendations=[
                "Human face showing emotion outperforms text-only by 40%",
                "3 elements max: face + text + background",
                "Text max 3 words — readable at 120px width",
                "High contrast between subject and background",
            ],
            optimization_tips=[
                "Test 2 versions: curiosity vs outcome",
                "Use arrow or eye direction to guide viewer to text",
                "Bright accent color draws the eye",
            ],
            virality_score=0.0,
            predicted_reach=0,
            predicted_engagement_rate=0.0,
            predicted_ctr=8.5,
        )

    async def generate_concept(self, title: str, style: str = "curiosity") -> dict[str, Any]:
        styles: dict[str, dict[str, str]] = {
            "curiosity": {
                "text": f"The truth about {title[:20]}",
                "visual": "Close-up face with shocked/surprised expression",
            },
            "outcome": {
                "text": f"{title[:20]} — REVEALED",
                "visual": "Action shot with result overlay",
            },
        }
        chosen = styles.get(style, {"text": title[:20], "visual": "Strong action image"})
        return {
            "title": title,
            "style": style,
            "text_overlay": chosen["text"],
            "visual_direction": chosen["visual"],
            "color_recommendation": "High contrast — dark subject, bright text",
            "emotion": "curiosity" if style == "curiosity" else "satisfaction",
            "ctr_prediction": "7-9%" if style == "curiosity" else "5-7%",
        }

    async def predict_ctr(self, concept: dict[str, Any]) -> dict[str, Any]:
        base = 6.0
        bonus = 1.5 if "face" in str(concept).lower() else 0.0
        bonus += 1.0 if len(concept.get("text_overlay", "")) <= 20 else 0.0
        ctr = base + bonus
        return {
            "predicted_ctr": f"{ctr:.1f}%",
            "benchmark": "5-6%",
            "vs_benchmark": f"+{ctr - 5.5:.1f}%",
            "recommendation": "Strong" if ctr > 7 else "Average — consider iteration",
        }

    async def analyze(self, data: dict[str, Any]) -> dict[str, Any]:
        return {
            "platform": "thumbnail",
            "ctr_benchmark": "5-6%",
            "top_performing_elements": ["Emotion face", "Short text", "High contrast"],
            "test_recommendation": "Always test 2 variants",
        }
