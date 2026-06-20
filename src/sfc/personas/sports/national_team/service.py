"""Saudi National Team Persona."""
from __future__ import annotations

import logging
from typing import Any

from sfc.personas.shared.types import PersonaCategory
from sfc.personas.sports.shared.base import BaseSportsPersona
from sfc.personas.sports.shared.models import InsightType, PersonaInsight

logger = logging.getLogger("sfc.personas.sports.national_team")


class NationalTeamPersona(BaseSportsPersona):
    PERSONA_ID = "SPORT-NATL-TEAM-01"
    PERSONA_NAME = "Saudi National Team Specialist"
    PERSONA_CATEGORY = PersonaCategory.INTELLIGENCE
    PERSONA_DESCRIPTION = (
        "Expert in Saudi national team players, coaches, tactics, qualifiers, and World Cup campaigns."
    )
    PERSONA_CAPABILITIES = [
        "squad_analysis",
        "match_analysis",
        "player_profiling",
        "opponent_scouting",
        "world_cup_preparation",
    ]
    PERSONA_PERFORMANCE_SCORE = 88.0

    async def generate_insight(self, context: dict[str, Any]) -> PersonaInsight:
        competition = context.get("competition", "Saudi Pro League")
        squad = context.get("players", [])
        return self._build_insight(
            context=context,
            insight_type=InsightType.ANALYSIS,
            title=f"National Team Intelligence — {competition}",
            summary=f"Comprehensive national team assessment for {competition}.",
            key_findings=[
                "National team squad reviewed",
                f"Competition: {competition}",
                f"{len(squad)} players assessed",
            ],
            recommendations=[
                "Focus on defensive organization",
                "Maximize set-piece opportunities",
            ],
            confidence_score=88.0,
            tags=["national_team", "saudi_arabia"],
            entities=squad[:5],
        )

    async def analyze(self, data: dict[str, Any]) -> dict[str, Any]:
        team = data.get("team", "Saudi Arabia")
        competition = data.get("competition", "World Cup Qualifier")
        return {
            "team": team,
            "competition": competition,
            "form": "strong",
            "tactical_shape": "4-3-3",
            "key_players": data.get("players", [])[:3],
            "analysis_summary": f"{team} analysis complete for {competition}",
        }

    async def generate_squad_report(self, players: list[str], competition: str) -> dict[str, Any]:
        """Generate a squad report for a competition."""
        return {
            "competition": competition,
            "squad_size": len(players),
            "analysis": f"Squad analysis for {competition}",
            "key_players": players[:3],
            "readiness_score": 82.0,
        }

    async def analyze_qualifier(self, match_data: dict[str, Any]) -> dict[str, Any]:
        """Analyze a World Cup qualifier match."""
        return {
            "home": match_data.get("home", "Saudi Arabia"),
            "away": match_data.get("away", "Opponent"),
            "qualification_impact": "high",
            "tactical_recommendation": "Press high, exploit flanks",
        }
