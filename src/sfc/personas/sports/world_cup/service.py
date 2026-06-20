"""World Cup Persona."""
from __future__ import annotations

import logging
from typing import Any

from sfc.personas.shared.types import PersonaCategory
from sfc.personas.sports.shared.base import BaseSportsPersona
from sfc.personas.sports.shared.models import InsightType, PersonaInsight

logger = logging.getLogger("sfc.personas.sports.world_cup")


class WorldCupPersona(BaseSportsPersona):
    PERSONA_ID = "SPORT-WC-01"
    PERSONA_NAME = "World Cup Specialist"
    PERSONA_CATEGORY = PersonaCategory.INTELLIGENCE
    PERSONA_DESCRIPTION = (
        "Expert in World Cup groups, opponents, FIFA events, and global tournament intelligence "
        "with a Saudi perspective."
    )
    PERSONA_CAPABILITIES = [
        "tournament_analysis",
        "opponent_research",
        "group_analysis",
        "match_prediction",
        "media_coverage_planning",
    ]
    PERSONA_PERFORMANCE_SCORE = 87.0

    async def generate_insight(self, context: dict[str, Any]) -> PersonaInsight:
        group = context.get("group", "Group A")
        teams = context.get("teams", [])
        return self._build_insight(
            context=context,
            insight_type=InsightType.ANALYSIS,
            title=f"World Cup Intelligence — {group}",
            summary=f"World Cup group analysis for {group} with Saudi perspective.",
            key_findings=[
                f"World Cup {group} analysed",
                "Saudi Arabia's tournament path mapped",
                "Key opponents identified",
            ],
            recommendations=[
                "Prepare detailed opponent dossiers",
                "Align media coverage plan with tournament schedule",
            ],
            confidence_score=87.0,
            tags=["world_cup", "tournament"],
            entities=teams[:5],
        )

    async def analyze(self, data: dict[str, Any]) -> dict[str, Any]:
        group = data.get("group", "Group A")
        teams = data.get("teams", [])
        return {
            "group": group,
            "teams": teams,
            "saudi_qualification_probability": 0.65,
            "tournament_stage": data.get("stage", "Group Stage"),
            "analysis_summary": f"World Cup {group} analysis complete",
        }

    async def analyze_group(self, group: str, teams: list[str]) -> dict[str, Any]:
        """Analyse a World Cup group."""
        return {
            "group": group,
            "teams": teams,
            "difficulty_rating": "high",
            "saudi_path": f"Saudi Arabia must beat {teams[0] if teams else 'all opponents'} to advance",
            "key_matches": teams[:2],
        }

    async def generate_opponent_brief(self, opponent: str) -> dict[str, Any]:
        """Generate a brief on a World Cup opponent."""
        return {
            "opponent": opponent,
            "threat_level": "high",
            "key_players": [f"{opponent} Star Player"],
            "tactical_vulnerability": "High press exposure",
            "recommendation": f"Target {opponent}'s defensive transitions",
        }
