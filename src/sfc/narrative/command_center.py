"""Narrative Command Center — orchestrates all narrative intelligence engines."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("sfc.narrative.command_center")

_singleton: "NarrativeCommandCenter | None" = None


def get_narrative_command_center() -> "NarrativeCommandCenter":
    global _singleton
    if _singleton is None:
        _singleton = NarrativeCommandCenter()
    return _singleton


class NarrativeCommandCenter:
    """Central orchestrator for narrative intelligence and audience modeling."""

    def __init__(self) -> None:
        self._modeling = None
        self._lifecycle = None
        self._forecasting = None
        self._risk = None
        self._strategy = None
        self._audience_modeling = None
        self._audience_segmentation = None
        self._audience_evolution = None
        self._influence_network = None
        self._reaction_simulator = None

    @property
    def modeling(self):
        if self._modeling is None:
            from sfc.narrative.modeling.service import get_narrative_modeling_service
            self._modeling = get_narrative_modeling_service()
        return self._modeling

    @property
    def lifecycle(self):
        if self._lifecycle is None:
            from sfc.narrative.lifecycle.service import get_lifecycle_engine
            self._lifecycle = get_lifecycle_engine()
        return self._lifecycle

    @property
    def forecasting(self):
        if self._forecasting is None:
            from sfc.narrative.forecasting.service import get_forecasting_engine
            self._forecasting = get_forecasting_engine()
        return self._forecasting

    @property
    def risk(self):
        if self._risk is None:
            from sfc.narrative.risk.service import get_risk_engine
            self._risk = get_risk_engine()
        return self._risk

    @property
    def strategy(self):
        if self._strategy is None:
            from sfc.narrative.strategy.service import get_strategy_engine
            self._strategy = get_strategy_engine()
        return self._strategy

    @property
    def audience_modeling(self):
        if self._audience_modeling is None:
            from sfc.audience.modeling.service import get_audience_modeling_engine
            self._audience_modeling = get_audience_modeling_engine()
        return self._audience_modeling

    @property
    def audience_segmentation(self):
        if self._audience_segmentation is None:
            from sfc.audience.segmentation.service import get_segmentation_engine
            self._audience_segmentation = get_segmentation_engine()
        return self._audience_segmentation

    @property
    def audience_evolution(self):
        if self._audience_evolution is None:
            from sfc.audience.evolution.service import get_evolution_engine
            self._audience_evolution = get_evolution_engine()
        return self._audience_evolution

    @property
    def influence_network(self):
        if self._influence_network is None:
            from sfc.influence.network.service import get_influence_network_engine
            self._influence_network = get_influence_network_engine()
        return self._influence_network

    @property
    def reaction_simulator(self):
        if self._reaction_simulator is None:
            from sfc.simulation.reaction.service import get_reaction_simulator
            self._reaction_simulator = get_reaction_simulator()
        return self._reaction_simulator

    async def run_full_intelligence(
        self, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Run complete narrative intelligence pipeline."""
        ctx = context or {}

        narrative_map = await self.modeling.build_narrative_map()
        profiles = narrative_map.profiles[:5]

        lifecycle_batch = await self.lifecycle.batch_analyze(
            [p.profile_id for p in profiles]
        )

        forecast_bundle = await self.forecasting.forecast_bundle(
            [p.profile_id for p in profiles]
        )

        risk_reports = []
        strategy_reports = []
        for profile in profiles[:3]:
            risk = await self.risk.assess_risk(profile)
            risk_reports.append(risk.to_dict())
            strategy = await self.strategy.recommend(profile, risk_report=risk)
            strategy_reports.append(strategy.to_dict())

        audience_twins = await self.audience_modeling.build_models()
        audience_model_report = await self.audience_modeling.generate_report(audience_twins)

        segments = await self.audience_segmentation.segment()
        segment_report = await self.audience_segmentation.generate_report(segments)

        evolution_report = await self.audience_evolution.analyze_evolution(
            segments=[s.to_dict() for s in segments]
        )

        network = await self.influence_network.map_network(context=ctx)

        war_room_escalations = [
            r for r in risk_reports
            if r.get("requires_war_room", False)
        ]

        return {
            "narrative_map": narrative_map.to_dict(),
            "lifecycle_batch": lifecycle_batch.to_dict(),
            "forecast_bundle": forecast_bundle.to_dict(),
            "risk_reports": risk_reports,
            "strategy_reports": strategy_reports,
            "audience_model_report": audience_model_report.to_dict(),
            "segment_report": segment_report.to_dict(),
            "evolution_report": evolution_report.to_dict(),
            "influence_network": network.to_dict(),
            "war_room_escalations": war_room_escalations,
            "total_narratives": narrative_map.total_active,
            "total_audience": audience_model_report.total_modeled_audience,
            "summary": self._build_summary(
                narrative_map, audience_model_report, war_room_escalations
            ),
        }

    async def simulate_scenario(
        self,
        scenario_name: str,
        narrative_id: str = "",
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Simulate public reaction to a specific scenario."""
        from sfc.simulation.reaction.models import SimulationScenario
        try:
            scenario = SimulationScenario(scenario_name)
        except ValueError:
            scenario = SimulationScenario.CLUB_STATEMENT

        forecast = await self.reaction_simulator.simulate(
            scenario=scenario,
            narrative_id=narrative_id,
            context=context or {},
        )
        return forecast.to_dict()

    def get_status(self) -> dict[str, Any]:
        return {
            "status": "active",
            "engines": {
                "narrative_modeling": "ready",
                "narrative_lifecycle": "ready",
                "narrative_forecasting": "ready",
                "narrative_risk": "ready",
                "narrative_strategy": "ready",
                "audience_modeling": "ready",
                "audience_segmentation": "ready",
                "audience_evolution": "ready",
                "influence_network": "ready",
                "reaction_simulator": "ready",
            },
        }

    def _build_summary(
        self,
        narrative_map: Any,
        audience_report: Any,
        escalations: list[dict[str, Any]],
    ) -> str:
        return (
            f"Narrative Intelligence: {narrative_map.total_active} active narratives tracked. "
            f"Audience: {audience_report.total_modeled_audience:,} modeled. "
            f"War room escalations: {len(escalations)}."
        )
