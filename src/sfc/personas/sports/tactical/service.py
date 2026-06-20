"""Football Tactical Analyst Persona."""
from __future__ import annotations

import logging
from typing import Any

from sfc.events.bus import get_event_bus
from sfc.personas.shared.types import PersonaCategory
from sfc.personas.sports.shared.base import BaseSportsPersona
from sfc.personas.sports.shared.events import TacticalAnalysisCompleted
from sfc.personas.sports.shared.models import InsightType, PersonaInsight

logger = logging.getLogger("sfc.personas.sports.tactical")


def _formation_strengths(formation: str) -> list[str]:
    _map: dict[str, list[str]] = {
        "4-3-3": ["Wide attacks", "High press", "Goal threat"],
        "4-2-3-1": ["Defensive solidity", "Counter-attack", "Midfield control"],
        "3-5-2": ["Wing-back overloads", "Numerical midfield advantage"],
    }
    return _map.get(formation, ["Flexible structure", "Tactical adaptability"])


def _formation_weaknesses(formation: str) -> list[str]:
    _map: dict[str, list[str]] = {
        "4-3-3": ["Exposed to counter", "High defensive line"],
        "4-2-3-1": ["Narrow flanks", "Transition vulnerability"],
        "3-5-2": ["Wide spaces when attacking", "Wing-back stamina"],
    }
    return _map.get(formation, ["Requires tactical discipline"])


class TacticalPersona(BaseSportsPersona):
    PERSONA_ID = "SPORT-TACTICAL-01"
    PERSONA_NAME = "Football Tactical Analyst"
    PERSONA_CATEGORY = PersonaCategory.ANALYTICS
    PERSONA_DESCRIPTION = (
        "Deep tactical analyst covering formations, pressing, build-up, "
        "transitions, and set-piece strategies."
    )
    PERSONA_CAPABILITIES = [
        "formation_analysis",
        "pressing_analysis",
        "build_up_analysis",
        "set_piece_analysis",
        "tactical_report_generation",
    ]
    PERSONA_PERFORMANCE_SCORE = 85.0

    async def generate_insight(self, context: dict[str, Any]) -> PersonaInsight:
        team = context.get("team", "")
        formation = context.get("formation", "4-3-3")
        insight = self._build_insight(
            context=context,
            insight_type=InsightType.ANALYSIS,
            title=f"Tactical Analysis — {team or 'General'}",
            summary=f"Tactical analysis for {team or 'target team'} using {formation}.",
            key_findings=[
                f"Tactical analysis for {team}",
                f"Formation {formation} assessed",
                "Key tactical patterns identified",
            ],
            recommendations=[
                "Implement recommended counter-tactics in training",
                "Review set-piece routines against identified weaknesses",
            ],
            confidence_score=85.0,
            tags=["tactical", "formation"],
            entities=[team] if team else [],
        )
        get_event_bus().publish(TacticalAnalysisCompleted(
            division="sports_personas",
            run_id=context.get("run_id", ""),
            payload={
                "team": team,
                "formation": formation,
                "insight_id": insight.insight_id,
            },
        ))
        return insight

    async def analyze(self, data: dict[str, Any]) -> dict[str, Any]:
        team = data.get("team", "")
        formation = data.get("formation", "4-3-3")
        return {
            "team": team,
            "formation": formation,
            "strengths": _formation_strengths(formation),
            "weaknesses": _formation_weaknesses(formation),
            "pressing_style": "high" if "4-3-3" in formation else "medium",
            "analysis_summary": f"Tactical analysis for {team} ({formation}) complete",
        }

    async def analyze_formation(self, formation: str, team: str) -> dict[str, Any]:
        """Analyse a team's formation."""
        return {
            "team": team,
            "formation": formation,
            "strengths": _formation_strengths(formation),
            "weaknesses": _formation_weaknesses(formation),
            "pressing_style": "high" if "4-3-3" in formation else "medium",
            "recommendation": f"Counter {formation} with compact mid-block",
        }

    async def match_tactical_report(
        self,
        home: str,
        away: str,
        home_formation: str = "4-3-3",
        away_formation: str = "4-2-3-1",
    ) -> dict[str, Any]:
        """Generate a match tactical report."""
        return {
            "home": home,
            "home_formation": home_formation,
            "away": away,
            "away_formation": away_formation,
            "key_battles": [
                f"{home} midfield vs {away} press",
                "Set pieces",
            ],
            "tactical_edge": home,
        }
