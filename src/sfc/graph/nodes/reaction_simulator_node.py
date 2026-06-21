"""LangGraph node — Reaction Simulator."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("sfc.graph.nodes.reaction_simulator")


async def reaction_simulator_node(state: dict[str, Any]) -> dict[str, Any]:
    """Simulate public reaction to the current content scenario."""
    try:
        from sfc.simulation.reaction.service import get_reaction_simulator
        from sfc.simulation.reaction.models import SimulationScenario
        simulator = get_reaction_simulator()
        context = state.get("context", {})
        scenario_name = context.get("scenario", SimulationScenario.CLUB_STATEMENT.value)
        try:
            scenario = SimulationScenario(scenario_name)
        except ValueError:
            scenario = SimulationScenario.CLUB_STATEMENT

        narrative_id = context.get("narrative_id", "")
        forecast = await simulator.simulate(
            scenario=scenario,
            narrative_id=narrative_id,
            context=context,
        )
        return {
            "reaction_forecast": forecast.to_dict(),
            "pipeline_stage": "reaction_simulator",
        }
    except Exception as exc:
        logger.warning("reaction_simulator_node failed: %s", exc)
        warnings = list(state.get("warnings", []))
        warnings.append(f"reaction_simulator_node: {exc}")
        return {
            "reaction_forecast": {},
            "pipeline_stage": "reaction_simulator",
            "warnings": warnings,
        }
