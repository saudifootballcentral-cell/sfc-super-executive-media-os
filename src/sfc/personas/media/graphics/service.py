"""Sports Graphics Specialist Persona."""
from __future__ import annotations

import logging
from typing import Any

from sfc.events.bus import get_event_bus
from sfc.personas.shared.types import PersonaCategory
from sfc.personas.media.shared.base import BaseMediaPersona
from sfc.personas.media.shared.models import ContentFormat, Platform, PlatformInsight
from sfc.personas.media.shared.events import GraphicCreated

logger = logging.getLogger("sfc.personas.media.graphics")


class GraphicsPersona(BaseMediaPersona):
    PERSONA_ID = "MEDIA-GRAPHICS-01"
    PERSONA_NAME = "Sports Graphics Specialist"
    PERSONA_CATEGORY = PersonaCategory.CREATIVE
    PERSONA_DESCRIPTION = (
        "Expert in sports data visualization, lineup graphics, match statistics, "
        "infographics, and instant-understanding visual design."
    )
    PERSONA_CAPABILITIES = [
        "lineup_design",
        "statistics_visualization",
        "infographic_creation",
        "match_card_design",
        "data_storytelling",
    ]
    PERSONA_PERFORMANCE_SCORE = 85.0
    PERSONA_PLATFORM = Platform.GRAPHICS

    async def generate_insight(self, context: dict[str, Any]) -> PlatformInsight:
        content_type = context.get("content_type", "match stats")
        get_event_bus().publish(
            GraphicCreated(
                division="media_personas",
                run_id=context.get("run_id", ""),
                payload={"content_type": content_type},
            )
        )
        return self._build_insight(
            context=context,
            content_format=ContentFormat.GRAPHIC,
            title=f"Graphics Strategy — {content_type}",
            summary=f"Sports data visualization strategy for {content_type}.",
            hook=f"The stat that explains everything: [{content_type}]",
            recommendations=[
                "One key number per graphic",
                "Lineup graphics perform 3x better with player faces",
                "Use Saudi Pro League brand guidelines",
                "Arabic numerals where appropriate",
            ],
            optimization_tips=[
                "Dark background with bright stats outperforms white backgrounds",
                "Animated versions outperform static by 40%",
                "Always include source credit",
            ],
            virality_score=76.0,
            predicted_reach=140000,
            predicted_engagement_rate=6.8,
        )

    async def design_lineup_graphic(
        self,
        home_team: str,
        away_team: str,
        home_players: list[str],
        away_players: list[str],
        formation_home: str = "4-3-3",
        formation_away: str = "4-2-3-1",
    ) -> dict[str, Any]:
        return {
            "graphic_type": "lineup_comparison",
            "home_team": home_team,
            "home_players": home_players,
            "home_formation": formation_home,
            "away_team": away_team,
            "away_players": away_players,
            "away_formation": formation_away,
            "design_notes": "Split layout, team crests centred, formation dots with player names",
            "data_points": [
                "Player names",
                "Shirt numbers",
                "Formation",
                "Key matchups highlighted",
            ],
            "dimensions": "1080x1080",
        }

    async def create_stat_infographic(
        self,
        stat_name: str,
        value: float | str,
        context_text: str = "",
    ) -> dict[str, Any]:
        return {
            "stat": stat_name,
            "value": value,
            "context": context_text or f"{stat_name}: {value}",
            "design": "Large number centred, context below, source bottom-right",
            "visual_metaphor": "Progress bar or comparison bars",
            "colour_coding": "Green for positive, red for negative stats",
            "animation_recommended": True,
        }

    async def analyze(self, data: dict[str, Any]) -> dict[str, Any]:
        return {
            "platform": "graphics",
            "most_shared_format": "lineup_graphic",
            "data_types": [
                "Match stats",
                "League table",
                "Player comparison",
                "Historical records",
            ],
            "arabic_localization": "required",
        }
