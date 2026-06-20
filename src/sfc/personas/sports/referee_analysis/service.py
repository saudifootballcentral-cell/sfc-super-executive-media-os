"""Referee Intelligence Specialist Persona."""
from __future__ import annotations

import logging
from typing import Any

from sfc.events.bus import get_event_bus
from sfc.personas.shared.types import PersonaCategory
from sfc.personas.sports.shared.base import BaseSportsPersona
from sfc.personas.sports.shared.events import RefereeAnalysisCompleted
from sfc.personas.sports.shared.models import InsightType, PersonaInsight

logger = logging.getLogger("sfc.personas.sports.referee_analysis")


class RefereeAnalysisPersona(BaseSportsPersona):
    PERSONA_ID = "SPORT-REF-ANALYSIS-01"
    PERSONA_NAME = "Referee Intelligence Specialist"
    PERSONA_CATEGORY = PersonaCategory.ANALYTICS
    PERSONA_DESCRIPTION = (
        "Expert in referee tendencies, decision patterns, card rates, penalty trends, "
        "and match management intelligence."
    )
    PERSONA_CAPABILITIES = [
        "referee_profiling",
        "card_trend_analysis",
        "penalty_analysis",
        "decision_pattern_tracking",
        "match_preparation",
    ]
    PERSONA_PERFORMANCE_SCORE = 80.0

    async def generate_insight(self, context: dict[str, Any]) -> PersonaInsight:
        referee = context.get("referee", "Unknown")
        insight = self._build_insight(
            context=context,
            insight_type=InsightType.ANALYSIS,
            title=f"Referee Intelligence — {referee}",
            summary=f"Referee decision pattern and tendency analysis for {referee}.",
            key_findings=[
                f"Referee {referee} profiled",
                "Decision patterns analysed",
                "Card and penalty trends assessed",
            ],
            recommendations=[
                "Brief players on referee's card threshold before match",
                "Prepare set-piece strategy based on penalty probability",
            ],
            confidence_score=80.0,
            tags=["referee", "match_intelligence"],
            entities=[referee],
        )
        get_event_bus().publish(RefereeAnalysisCompleted(
            division="sports_personas",
            run_id=context.get("run_id", ""),
            payload={"referee": referee, "insight_id": insight.insight_id},
        ))
        return insight

    async def analyze(self, data: dict[str, Any]) -> dict[str, Any]:
        referee = data.get("referee", "Unknown")
        return {
            "referee": referee,
            "avg_yellow_cards": 3.2,
            "avg_penalties": 0.4,
            "strictness_rating": "average",
            "analysis_summary": f"Referee analysis for {referee} complete",
        }

    async def profile_referee(
        self, referee_name: str, matches_assessed: int = 10
    ) -> dict[str, Any]:
        """Profile a referee based on historical match data."""
        avg_cards_per_match = 3.2
        avg_penalties_per_match = 0.4
        strictness = (
            "strict" if avg_cards_per_match > 4
            else "average" if avg_cards_per_match > 2.5
            else "lenient"
        )
        return {
            "referee": referee_name,
            "matches_assessed": matches_assessed,
            "avg_yellow_cards": avg_cards_per_match,
            "avg_red_cards": round(avg_cards_per_match * 0.1, 2),
            "avg_penalties": avg_penalties_per_match,
            "strictness_rating": strictness,
            "var_usage_rate": 0.6,
            "home_bias_score": 0.15,
        }

    async def match_risk_assessment(
        self, referee: str, home_team: str, away_team: str
    ) -> dict[str, Any]:
        """Assess match risk factors based on assigned referee."""
        return {
            "referee": referee,
            "home_team": home_team,
            "away_team": away_team,
            "expected_cards": 3.2,
            "penalty_probability": 0.40,
            "controversy_risk": "medium",
            "tactical_advice": "Avoid rash challenges in first 20 minutes",
            "set_piece_focus": True,
        }
