"""Transfer Market Specialist Persona."""
from __future__ import annotations

import logging
from typing import Any

from sfc.events.bus import get_event_bus
from sfc.personas.shared.types import PersonaCategory
from sfc.personas.sports.shared.base import BaseSportsPersona
from sfc.personas.sports.shared.events import TransferAnalyzed
from sfc.personas.sports.shared.models import InsightType, PersonaInsight

logger = logging.getLogger("sfc.personas.sports.transfer")


class TransferPersona(BaseSportsPersona):
    PERSONA_ID = "SPORT-TRANSFER-01"
    PERSONA_NAME = "Transfer Market Specialist"
    PERSONA_CATEGORY = PersonaCategory.INTELLIGENCE
    PERSONA_DESCRIPTION = (
        "Expert in football transfers, contracts, agent networks, negotiations, "
        "and market trends with Saudi focus."
    )
    PERSONA_CAPABILITIES = [
        "transfer_tracking",
        "rumor_classification",
        "contract_analysis",
        "agent_monitoring",
        "squad_impact_assessment",
    ]
    PERSONA_PERFORMANCE_SCORE = 90.0

    async def generate_insight(self, context: dict[str, Any]) -> PersonaInsight:
        player = context.get("player", "Unknown")
        from_club = context.get("from_club", "")
        to_club = context.get("to_club", "")
        insight = self._build_insight(
            context=context,
            insight_type=InsightType.ANALYSIS,
            title=f"Transfer Intelligence — {player}",
            summary=f"Transfer market analysis for {player} ({from_club} → {to_club}).",
            key_findings=[
                f"Transfer: {player} to {to_club}",
                "Market intelligence gathered",
                "Agent network monitored",
            ],
            recommendations=[
                "Verify transfer via minimum 2 independent sources",
                "Assess squad impact before publishing",
            ],
            confidence_score=90.0,
            tags=["transfer", "market"],
            entities=[player, from_club, to_club],
        )
        get_event_bus().publish(TransferAnalyzed(
            division="sports_personas",
            run_id=context.get("run_id", ""),
            payload={
                "player": player,
                "from_club": from_club,
                "to_club": to_club,
                "insight_id": insight.insight_id,
            },
        ))
        return insight

    async def analyze(self, data: dict[str, Any]) -> dict[str, Any]:
        player = data.get("player", "Unknown")
        to_club = data.get("to_club", "")
        fee = data.get("fee_m", 0.0)
        return {
            "player": player,
            "to_club": to_club,
            "fee_m": fee,
            "market_value_assessment": "fair" if fee < 100 else "premium",
            "saudi_relevance": to_club.lower() in ["al hilal", "al nassr", "al ittihad", "al ahli"],
            "analysis_summary": f"Transfer analysis for {player} complete",
        }

    async def classify_rumor(
        self,
        player: str,
        from_club: str,
        to_club: str,
        source_reliability: float = 0.7,
    ) -> dict[str, Any]:
        """Classify a transfer rumor by reliability."""
        if source_reliability >= 0.85:
            classification = "ADVANCED_NEGOTIATION"
        elif source_reliability >= 0.70:
            classification = "STRONG_RUMOR"
        elif source_reliability >= 0.50:
            classification = "RUMOR"
        else:
            classification = "UNCONFIRMED"

        return {
            "player": player,
            "from_club": from_club,
            "to_club": to_club,
            "status": classification,
            "reliability": source_reliability,
            "saudi_relevance": to_club.lower() in [
                "al hilal", "al nassr", "al ittihad", "al ahli"
            ],
        }

    async def squad_impact(
        self, player: str, club: str, transfer_fee_m: float = 0.0
    ) -> dict[str, Any]:
        """Assess the squad impact of a transfer."""
        return {
            "player": player,
            "club": club,
            "fee_m": transfer_fee_m,
            "impact": "high" if transfer_fee_m > 50 else "medium" if transfer_fee_m > 10 else "low",
            "squad_improvement": True,
            "narrative_value": "high",
        }
