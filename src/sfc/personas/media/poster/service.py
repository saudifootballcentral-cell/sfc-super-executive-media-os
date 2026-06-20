"""Sports Poster Specialist Persona."""
from __future__ import annotations

import logging
from typing import Any

from sfc.events.bus import get_event_bus
from sfc.personas.shared.types import PersonaCategory
from sfc.personas.media.shared.base import BaseMediaPersona
from sfc.personas.media.shared.models import ContentFormat, Platform, PlatformInsight
from sfc.personas.media.shared.events import PosterCreated

logger = logging.getLogger("sfc.personas.media.poster")


class PosterPersona(BaseMediaPersona):
    PERSONA_ID = "MEDIA-POSTER-01"
    PERSONA_NAME = "Sports Poster Specialist"
    PERSONA_CATEGORY = PersonaCategory.CREATIVE
    PERSONA_DESCRIPTION = (
        "Expert in match poster design, player poster creation, tournament visuals, "
        "and campaign poster direction for Saudi football."
    )
    PERSONA_CAPABILITIES = [
        "match_poster_design",
        "player_poster_direction",
        "tournament_visual_design",
        "campaign_creative_direction",
        "brand_consistency",
    ]
    PERSONA_PERFORMANCE_SCORE = 83.0
    PERSONA_PLATFORM = Platform.POSTER

    async def generate_insight(self, context: dict[str, Any]) -> PlatformInsight:
        match = context.get("match", "Al Hilal vs Al Nassr")
        get_event_bus().publish(
            PosterCreated(
                division="media_personas",
                run_id=context.get("run_id", ""),
                payload={"match": match},
            )
        )
        return self._build_insight(
            context=context,
            content_format=ContentFormat.GRAPHIC,
            title=f"Poster Strategy — {match}",
            summary=f"Match poster direction for {match}.",
            hook="The poster that makes them feel the game before they attend.",
            recommendations=[
                "Hero image dominates 70% of frame",
                "Match details in bottom third — readable at a glance",
                "Use team colours — one per side for rivalries",
                "Arabic and English text required",
            ],
            optimization_tips=[
                "Club crests at equal prominence for derbies",
                "Kickoff time in bold — this is what fans look for first",
                "Limited colour palette: 3 max",
            ],
            virality_score=75.0,
            predicted_reach=85000,
            predicted_engagement_rate=5.5,
        )

    async def generate_match_poster_brief(
        self,
        home_team: str,
        away_team: str,
        date: str,
        venue: str = "",
    ) -> dict[str, Any]:
        return {
            "home_team": home_team,
            "away_team": away_team,
            "date": date,
            "venue": venue or "TBA",
            "design_direction": f"Split composition: {home_team} left / {away_team} right",
            "hero_imagery": "Action player shots facing each other",
            "typography": "Bold uppercase match title + date/time prominent",
            "color_palette": [
                f"{home_team} primary color",
                f"{away_team} primary color",
                "Neutral dark background",
            ],
            "arabic_text_required": True,
            "dimensions": ["1080x1080 (Social)", "1080x1920 (Stories)", "A3 (Print)"],
        }

    async def create_player_poster_brief(
        self,
        player_name: str,
        team: str,
        occasion: str = "celebration",
    ) -> dict[str, Any]:
        return {
            "player": player_name,
            "team": team,
            "occasion": occasion,
            "composition": "Full-body action or celebration pose, off-center",
            "background": "Gradient using team colours with crowd blur",
            "text_elements": [player_name.upper(), team, occasion.title()],
            "mood": "heroic" if occasion == "celebration" else "intense",
            "format": "Vertical 9:16 preferred",
        }

    async def analyze(self, data: dict[str, Any]) -> dict[str, Any]:
        return {
            "platform": "poster",
            "key_elements": ["Hero image", "Match details", "Club branding"],
            "brand_consistency": "mandatory",
            "formats_required": ["Social square", "Stories vertical", "Print A3"],
        }
