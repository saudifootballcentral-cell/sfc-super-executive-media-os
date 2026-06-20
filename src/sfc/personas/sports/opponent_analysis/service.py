"""Opponent Intelligence Specialist Persona."""
from __future__ import annotations

import logging
from typing import Any

from sfc.events.bus import get_event_bus
from sfc.personas.shared.types import PersonaCategory
from sfc.personas.sports.shared.base import BaseSportsPersona
from sfc.personas.sports.shared.events import OpponentAnalyzed
from sfc.personas.sports.shared.models import InsightType, PersonaInsight

logger = logging.getLogger("sfc.personas.sports.opponent_analysis")


class OpponentAnalysisPersona(BaseSportsPersona):
    PERSONA_ID = "SPORT-OPP-ANALYSIS-01"
    PERSONA_NAME = "Opponent Intelligence Specialist"
    PERSONA_CATEGORY = PersonaCategory.INTELLIGENCE
    PERSONA_DESCRIPTION = (
        "Specialist in detailed opponent scouting, threat assessment, "
        "and match preparation intelligence."
    )
    PERSONA_CAPABILITIES = [
        "opponent_scouting",
        "threat_assessment",
        "weakness_identification",
        "match_preparation",
        "dossier_generation",
    ]
    PERSONA_PERFORMANCE_SCORE = 86.0

    async def generate_insight(self, context: dict[str, Any]) -> PersonaInsight:
        opponent = context.get("opponent", "Unknown")
        insight = self._build_insight(
            context=context,
            insight_type=InsightType.ANALYSIS,
            title=f"Opponent Intelligence — {opponent}",
            summary=f"Comprehensive scouting report on {opponent}.",
            key_findings=[
                f"Opponent {opponent} analysed",
                "Key threats identified",
                "Tactical vulnerabilities mapped",
            ],
            recommendations=[
                "Exploit identified defensive weaknesses",
                "Prepare targeted set-piece routines",
            ],
            confidence_score=86.0,
            tags=["opponent", "scouting"],
            entities=[opponent],
        )
        get_event_bus().publish(OpponentAnalyzed(
            division="sports_personas",
            run_id=context.get("run_id", ""),
            payload={"opponent": opponent, "insight_id": insight.insight_id},
        ))
        return insight

    async def analyze(self, data: dict[str, Any]) -> dict[str, Any]:
        opponent = data.get("opponent", "Unknown")
        competition = data.get("competition", "Saudi Pro League")
        return {
            "opponent": opponent,
            "competition": competition,
            "threat_level": "high",
            "scouted": True,
            "analysis_summary": f"Opponent analysis for {opponent} complete",
        }

    async def generate_dossier(
        self, opponent: str, competition: str = "Saudi Pro League"
    ) -> dict[str, Any]:
        """Generate a detailed opponent dossier."""
        return {
            "opponent": opponent,
            "competition": competition,
            "threat_level": "high",
            "key_players": [f"{opponent} Striker", f"{opponent} Playmaker"],
            "tactical_system": "4-2-3-1",
            "weaknesses": ["High defensive line", "Set piece vulnerability"],
            "recommended_approach": f"Press {opponent} high and exploit defensive line",
        }

    async def threat_assessment(
        self, opponent: str, match_type: str = "league"
    ) -> dict[str, Any]:
        """Assess the threat level of an opponent."""
        return {
            "opponent": opponent,
            "match_type": match_type,
            "overall_threat": 7.5,
            "attacking_threat": 7.0,
            "defensive_solidity": 7.8,
            "key_threat": f"{opponent}'s counter-attacking pace",
            "mitigation": "Maintain compact defensive shape",
        }
