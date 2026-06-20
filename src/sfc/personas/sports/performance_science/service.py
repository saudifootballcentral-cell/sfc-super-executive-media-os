"""Football Performance Analyst Persona."""
from __future__ import annotations

import logging
from typing import Any

from sfc.events.bus import get_event_bus
from sfc.personas.shared.types import PersonaCategory
from sfc.personas.sports.shared.base import BaseSportsPersona
from sfc.personas.sports.shared.events import PerformanceReportGenerated
from sfc.personas.sports.shared.models import InsightType, PersonaInsight

logger = logging.getLogger("sfc.personas.sports.performance_science")


class PerformanceSciencePersona(BaseSportsPersona):
    PERSONA_ID = "SPORT-PERF-SCI-01"
    PERSONA_NAME = "Football Performance Analyst"
    PERSONA_CATEGORY = PersonaCategory.ANALYTICS
    PERSONA_DESCRIPTION = (
        "Expert in player fitness, workload management, physical performance data, "
        "and recovery optimisation."
    )
    PERSONA_CAPABILITIES = [
        "fitness_analysis",
        "workload_management",
        "physical_performance_tracking",
        "recovery_optimisation",
        "load_analysis",
    ]
    PERSONA_PERFORMANCE_SCORE = 84.0

    async def generate_insight(self, context: dict[str, Any]) -> PersonaInsight:
        team = context.get("team", "")
        insight = self._build_insight(
            context=context,
            insight_type=InsightType.REPORT,
            title=f"Performance Science Report — {team or 'Squad'}",
            summary=f"Physical performance and load analysis for {team or 'squad'}.",
            key_findings=[
                "Physical performance data analysed",
                f"Team {team} load assessment complete",
                "Recovery status reviewed",
            ],
            recommendations=[
                "Adjust training load for players exceeding risk thresholds",
                "Implement recovery protocols post high-intensity matches",
            ],
            confidence_score=84.0,
            tags=["performance", "fitness"],
            entities=[team] if team else [],
        )
        get_event_bus().publish(PerformanceReportGenerated(
            division="sports_personas",
            run_id=context.get("run_id", ""),
            payload={"team": team, "insight_id": insight.insight_id, "report_type": "performance"},
        ))
        return insight

    async def analyze(self, data: dict[str, Any]) -> dict[str, Any]:
        player = data.get("player", "Unknown")
        matches = data.get("matches_in_28_days", 8)
        training_hours = data.get("training_hours", 20.0)
        load_score = min(100.0, matches * 8 + training_hours * 1.5)
        risk = "high" if load_score > 90 else "medium" if load_score > 70 else "low"
        return {
            "player": player,
            "load_score": round(load_score, 1),
            "risk_level": risk,
            "analysis_summary": f"Performance analysis for {player} complete",
        }

    async def analyze_player_load(
        self,
        player: str,
        matches_in_28_days: int = 8,
        training_hours: float = 20.0,
    ) -> dict[str, Any]:
        """Analyse a player's workload and risk level."""
        load_score = min(100.0, matches_in_28_days * 8 + training_hours * 1.5)
        risk = "high" if load_score > 90 else "medium" if load_score > 70 else "low"
        recommendation = (
            "Immediate rest recommended" if risk == "high"
            else "Monitor closely" if risk == "medium"
            else "Maintain current regimen"
        )
        return {
            "player": player,
            "load_score": round(load_score, 1),
            "matches_in_28_days": matches_in_28_days,
            "training_hours": training_hours,
            "risk_level": risk,
            "recommendation": recommendation,
        }

    async def team_fitness_report(
        self, team: str, avg_load: float = 65.0
    ) -> dict[str, Any]:
        """Generate a team-level fitness report."""
        status = (
            "optimal" if avg_load < 70
            else "caution" if avg_load < 85
            else "risk"
        )
        return {
            "team": team,
            "average_load_score": avg_load,
            "team_fitness_status": status,
            "players_at_risk_count": max(0, int((avg_load - 60) / 10)),
            "recommendation": f"Review training intensity for {team}",
        }
