"""Player Availability Specialist Persona."""
from __future__ import annotations

import logging
from typing import Any

from sfc.events.bus import get_event_bus
from sfc.personas.shared.types import PersonaCategory
from sfc.personas.sports.shared.base import BaseSportsPersona
from sfc.personas.sports.shared.events import PerformanceReportGenerated
from sfc.personas.sports.shared.models import InsightType, PersonaInsight

logger = logging.getLogger("sfc.personas.sports.injury_intelligence")

_RECOVERY_MAP: dict[str, int] = {
    "muscle": 14,
    "ligament": 90,
    "fracture": 60,
    "concussion": 7,
    "fatigue": 3,
}


class InjuryIntelligencePersona(BaseSportsPersona):
    PERSONA_ID = "SPORT-INJURY-INT-01"
    PERSONA_NAME = "Player Availability Specialist"
    PERSONA_CATEGORY = PersonaCategory.ANALYTICS
    PERSONA_DESCRIPTION = (
        "Expert in player injuries, recovery timelines, fitness status, "
        "and squad availability intelligence."
    )
    PERSONA_CAPABILITIES = [
        "injury_tracking",
        "recovery_monitoring",
        "availability_forecasting",
        "fitness_assessment",
        "squad_planning",
    ]
    PERSONA_PERFORMANCE_SCORE = 85.0

    async def generate_insight(self, context: dict[str, Any]) -> PersonaInsight:
        player = context.get("player", "Squad")
        insight = self._build_insight(
            context=context,
            insight_type=InsightType.REPORT,
            title=f"Injury Intelligence — {player}",
            summary=f"Player availability and injury status report for {player}.",
            key_findings=[
                f"Injury intelligence for {player} assessed",
                "Recovery timelines reviewed",
                "Squad availability mapped",
            ],
            recommendations=[
                "Prioritise medical clearance before selection",
                "Implement load management for high-risk players",
            ],
            confidence_score=85.0,
            tags=["injury", "availability"],
            entities=[player],
        )
        get_event_bus().publish(PerformanceReportGenerated(
            division="sports_personas",
            run_id=context.get("run_id", ""),
            payload={"player": player, "insight_id": insight.insight_id, "report_type": "injury"},
        ))
        return insight

    async def analyze(self, data: dict[str, Any]) -> dict[str, Any]:
        player = data.get("player", "Unknown")
        injury_type = data.get("injury_type", "muscle")
        days_injured = data.get("days_injured", 0)
        recovery = _RECOVERY_MAP.get(injury_type.lower(), 21)
        return {
            "player": player,
            "injury_type": injury_type,
            "estimated_recovery_days": max(recovery - days_injured, 0),
            "availability": "available" if days_injured > recovery else "injured",
            "analysis_summary": f"Injury analysis for {player} complete",
        }

    async def assess_injury(
        self, player: str, injury_type: str, days_injured: int = 0
    ) -> dict[str, Any]:
        """Assess a player's injury and estimate recovery."""
        recovery = _RECOVERY_MAP.get(injury_type.lower(), 21)
        return {
            "player": player,
            "injury_type": injury_type,
            "estimated_recovery_days": max(recovery - days_injured, 0),
            "availability": "available" if days_injured > recovery else "injured",
            "risk_of_recurrence": "medium" if "muscle" in injury_type.lower() else "low",
            "recommendation": f"Monitor {player} daily until cleared",
        }

    async def squad_availability_report(
        self, squad: list[str], injuries: dict[str, str]
    ) -> dict[str, Any]:
        """Generate a squad availability report."""
        total = len(squad)
        injured_count = len(injuries)
        available = total - injured_count
        rate = round(available / max(total, 1) * 100, 1)
        return {
            "total_squad": total,
            "available": available,
            "injured": injured_count,
            "availability_rate": rate,
            "injured_players": list(injuries.keys()),
            "recommendation": (
                "Squad has sufficient cover"
                if injured_count < 3
                else "Squad depth at risk"
            ),
        }
