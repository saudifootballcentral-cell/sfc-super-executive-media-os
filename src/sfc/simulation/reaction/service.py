"""Public Reaction Simulator — simulates audience response to content and events."""

from __future__ import annotations

import logging
import random
from typing import Any

from sfc.simulation.reaction.models import (
    AudienceReactionForecast,
    MediaReaction,
    ReactionForecast,
    ReactionType,
    SimulationScenario,
    SponsorReaction,
)

logger = logging.getLogger("sfc.simulation.reaction")

_singleton: "PublicReactionSimulator | None" = None


def get_reaction_simulator() -> "PublicReactionSimulator":
    global _singleton
    if _singleton is None:
        _singleton = PublicReactionSimulator()
    return _singleton


class PublicReactionSimulator:
    """Simulates how different audience segments react to content and events."""

    def __init__(self) -> None:
        self._gateway = None
        self._simulations: list[ReactionForecast] = []
        self._max_history = 500

    @property
    def gateway(self):
        if self._gateway is None:
            from sfc.ai.model_gateway import get_ai_gateway
            self._gateway = get_ai_gateway()
        return self._gateway

    async def simulate(
        self,
        scenario: SimulationScenario,
        narrative_id: str = "",
        content_description: str = "",
        context: dict[str, Any] | None = None,
    ) -> ReactionForecast:
        """Simulate public reaction to a given scenario."""
        ctx = context or {}
        audience_reactions = self._simulate_audience_reactions(scenario, ctx)
        sponsor_reaction = self._simulate_sponsor_reaction(scenario, ctx)
        media_reaction = await self._simulate_media_reaction(scenario, ctx)

        overall_positive = round(
            sum(r.positive_probability for r in audience_reactions) / max(len(audience_reactions), 1),
            1,
        )
        overall_negative = round(
            sum(r.negative_probability for r in audience_reactions) / max(len(audience_reactions), 1),
            1,
        )
        overall_controversy = round(
            sum(r.controversy_probability for r in audience_reactions) / max(len(audience_reactions), 1),
            1,
        )
        expected_sentiment_delta = round((overall_positive - overall_negative) / 2, 1)
        risk_score = self._compute_risk_score(overall_negative, overall_controversy, sponsor_reaction)
        proceed = risk_score < 70 and overall_negative < 50

        ai_analysis = await self._get_ai_analysis(
            scenario, overall_positive, overall_negative, risk_score
        )

        forecast = ReactionForecast(
            scenario=scenario,
            narrative_id=narrative_id,
            content_description=content_description,
            audience_reactions=audience_reactions,
            sponsor_reaction=sponsor_reaction,
            media_reaction=media_reaction,
            overall_positive_probability=overall_positive,
            overall_negative_probability=overall_negative,
            overall_controversy_risk=overall_controversy,
            expected_sentiment_delta=expected_sentiment_delta,
            expected_reach_multiplier=round(1.0 + overall_positive / 100, 2),
            risk_score=risk_score,
            risk_narrative=self._get_risk_narrative(scenario, risk_score),
            recommended_timing=self._get_optimal_timing(scenario),
            proceed_recommendation=proceed,
            ai_analysis=ai_analysis,
        )

        if len(self._simulations) < self._max_history:
            self._simulations.append(forecast)

        return forecast

    async def batch_simulate(
        self,
        scenarios: list[SimulationScenario],
        context: dict[str, Any] | None = None,
    ) -> list[ReactionForecast]:
        """Run simulations for multiple scenarios."""
        return [await self.simulate(scenario, context=context) for scenario in scenarios[:10]]

    def get_history(self, limit: int = 50) -> list[dict[str, Any]]:
        return [f.to_dict() for f in self._simulations[-limit:]]

    def _simulate_audience_reactions(
        self, scenario: SimulationScenario, context: dict[str, Any]
    ) -> list[AudienceReactionForecast]:
        scenario_profiles = {
            SimulationScenario.MATCH_WIN: (70, 15, 15, 0.05),
            SimulationScenario.MATCH_LOSS: (20, 30, 50, 0.25),
            SimulationScenario.TRANSFER_ANNOUNCEMENT: (65, 20, 15, 0.20),
            SimulationScenario.PLAYER_SCANDAL: (10, 25, 65, 0.55),
            SimulationScenario.TITLE_WIN: (90, 5, 5, 0.05),
            SimulationScenario.TOURNAMENT_EXIT: (15, 20, 65, 0.40),
            SimulationScenario.COACH_CHANGE: (40, 30, 30, 0.30),
            SimulationScenario.CLUB_STATEMENT: (50, 30, 20, 0.15),
            SimulationScenario.SPONSORSHIP_DEAL: (55, 35, 10, 0.10),
            SimulationScenario.REFEREE_CONTROVERSY: (15, 15, 70, 0.60),
        }
        base_pos, base_neu, base_neg, base_controversy = scenario_profiles.get(
            scenario, (50, 30, 20, 0.20)
        )

        audience_types = ["core_fans", "casual_fans", "national_team_fans", "media_followers"]
        reactions = []
        for aud_type in audience_types:
            noise = random.uniform(0.85, 1.15)
            reactions.append(AudienceReactionForecast(
                audience_type=aud_type,
                positive_probability=round(min(base_pos * noise, 99), 1),
                neutral_probability=round(base_neu * noise, 1),
                negative_probability=round(min(base_neg / noise, 99), 1),
                expected_engagement_multiplier=round(1 + base_pos / 100, 2),
                expected_sentiment_shift=round((base_pos - base_neg) / 4, 1),
                controversy_probability=round(base_controversy * 100 * random.uniform(0.8, 1.2), 1),
            ))

        return reactions

    def _simulate_sponsor_reaction(
        self, scenario: SimulationScenario, context: dict[str, Any]
    ) -> SponsorReaction:
        positive_scenarios = {
            SimulationScenario.MATCH_WIN,
            SimulationScenario.TITLE_WIN,
            SimulationScenario.TRANSFER_ANNOUNCEMENT,
            SimulationScenario.SPONSORSHIP_DEAL,
        }
        negative_scenarios = {
            SimulationScenario.PLAYER_SCANDAL,
            SimulationScenario.TOURNAMENT_EXIT,
            SimulationScenario.REFEREE_CONTROVERSY,
        }

        if scenario in positive_scenarios:
            risk = "low"
            revenue_impact = random.uniform(5, 20)
            rep_risk = random.uniform(0, 15)
            response = "Expected positive sponsor engagement"
            mitigation = False
        elif scenario in negative_scenarios:
            risk = "high"
            revenue_impact = random.uniform(-15, -5)
            rep_risk = random.uniform(40, 70)
            response = "Sponsors may distance temporarily — monitor and brief"
            mitigation = True
        else:
            risk = "medium"
            revenue_impact = random.uniform(-5, 10)
            rep_risk = random.uniform(10, 35)
            response = "Neutral sponsor reaction expected"
            mitigation = False

        return SponsorReaction(
            sponsor_type="primary_sponsor",
            risk_level=risk,
            estimated_revenue_impact=round(revenue_impact, 1),
            reputation_risk_score=round(rep_risk, 1),
            likely_response=response,
            mitigation_needed=mitigation,
        )

    async def _simulate_media_reaction(
        self, scenario: SimulationScenario, context: dict[str, Any]
    ) -> MediaReaction:
        high_coverage = {
            SimulationScenario.TITLE_WIN,
            SimulationScenario.TRANSFER_ANNOUNCEMENT,
            SimulationScenario.PLAYER_SCANDAL,
            SimulationScenario.TOURNAMENT_EXIT,
        }
        coverage_prob = 90.0 if scenario in high_coverage else 60.0

        negative_scenarios = {
            SimulationScenario.PLAYER_SCANDAL,
            SimulationScenario.MATCH_LOSS,
            SimulationScenario.TOURNAMENT_EXIT,
            SimulationScenario.REFEREE_CONTROVERSY,
        }
        tone = "negative" if scenario in negative_scenarios else "positive"

        framing_map = {
            SimulationScenario.TITLE_WIN: "Historic achievement for Saudi football",
            SimulationScenario.PLAYER_SCANDAL: "Reputational crisis for Saudi club",
            SimulationScenario.TRANSFER_ANNOUNCEMENT: "Saudi football's global ambition grows",
            SimulationScenario.TOURNAMENT_EXIT: "Questions over Saudi football development",
        }

        return MediaReaction(
            coverage_probability=round(coverage_prob * random.uniform(0.9, 1.1), 1),
            tone_forecast=tone,
            amplification_factor=round(random.uniform(1.2, 3.5), 1),
            narrative_framing=framing_map.get(scenario, f"Saudi football {scenario.value.replace('_', ' ')}"),
            key_outlets=["Saudi Sports TV", "Arabic Football Analysis", "Gulf Football Review"],
        )

    def _compute_risk_score(
        self,
        negative_prob: float,
        controversy_risk: float,
        sponsor: SponsorReaction,
    ) -> float:
        sponsor_risk = sponsor.reputation_risk_score
        score = negative_prob * 0.4 + controversy_risk * 0.35 + sponsor_risk * 0.25
        return round(min(score, 100), 1)

    def _get_risk_narrative(self, scenario: SimulationScenario, risk_score: float) -> str:
        if risk_score >= 70:
            return f"HIGH RISK: {scenario.value.replace('_', ' ').title()} poses significant reputational threat"
        if risk_score >= 40:
            return f"MODERATE RISK: Monitor {scenario.value.replace('_', ' ')} closely"
        return f"LOW RISK: {scenario.value.replace('_', ' ').title()} scenario is manageable"

    def _get_optimal_timing(self, scenario: SimulationScenario) -> str:
        timing_map = {
            SimulationScenario.MATCH_WIN: "Within 30 minutes of final whistle",
            SimulationScenario.TRANSFER_ANNOUNCEMENT: "Friday 18:00-20:00 UTC for maximum reach",
            SimulationScenario.TITLE_WIN: "Immediately — ride the peak sentiment wave",
            SimulationScenario.CLUB_STATEMENT: "Morning (09:00 UTC) for news cycle pickup",
        }
        return timing_map.get(scenario, "Peak hours: 19:00-22:00 UTC")

    async def _get_ai_analysis(
        self,
        scenario: SimulationScenario,
        positive: float,
        negative: float,
        risk: float,
    ) -> str:
        try:
            from sfc.ai.models import ModelRequest
            req = ModelRequest(
                prompt=f"Reaction simulation for {scenario.value}: positive={positive:.0f}%, negative={negative:.0f}%, risk={risk:.0f}",
                task_type="reaction_simulation",
                max_tokens=200,
            )
            resp = await self.gateway.complete(req)
            return resp.content
        except Exception:
            dominant = "positive" if positive > negative else "negative"
            return (
                f"Simulation of {scenario.value.replace('_', ' ')}: {dominant} reaction expected "
                f"({positive:.0f}% positive, {negative:.0f}% negative). "
                f"Risk score: {risk:.0f}/100."
            )
