"""Sports Intelligence Persona LangGraph nodes — standalone, not wired into main graph."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("sfc.graph.nodes.sports_personas")


async def national_team_persona_node(state: dict[str, Any]) -> dict[str, Any]:
    from sfc.personas.sports.national_team.service import NationalTeamPersona
    persona = NationalTeamPersona()
    insight = await persona.generate_insight(state.get("task_payload", {}))
    return {
        "sports_persona_insight": insight.model_dump(),
        "pipeline_stage": "national_team_persona_complete",
    }


async def spl_persona_node(state: dict[str, Any]) -> dict[str, Any]:
    from sfc.personas.sports.spl.service import SPLPersona
    persona = SPLPersona()
    insight = await persona.generate_insight(state.get("task_payload", {}))
    return {
        "sports_persona_insight": insight.model_dump(),
        "pipeline_stage": "spl_persona_complete",
    }


async def world_cup_persona_node(state: dict[str, Any]) -> dict[str, Any]:
    from sfc.personas.sports.world_cup.service import WorldCupPersona
    persona = WorldCupPersona()
    insight = await persona.generate_insight(state.get("task_payload", {}))
    return {
        "sports_persona_insight": insight.model_dump(),
        "pipeline_stage": "world_cup_persona_complete",
    }


async def afc_persona_node(state: dict[str, Any]) -> dict[str, Any]:
    from sfc.personas.sports.afc.service import AFCPersona
    persona = AFCPersona()
    insight = await persona.generate_insight(state.get("task_payload", {}))
    return {
        "sports_persona_insight": insight.model_dump(),
        "pipeline_stage": "afc_persona_complete",
    }


async def fifa_persona_node(state: dict[str, Any]) -> dict[str, Any]:
    from sfc.personas.sports.fifa.service import FIFAPersona
    persona = FIFAPersona()
    insight = await persona.generate_insight(state.get("task_payload", {}))
    return {
        "sports_persona_insight": insight.model_dump(),
        "pipeline_stage": "fifa_persona_complete",
    }


async def transfer_persona_node(state: dict[str, Any]) -> dict[str, Any]:
    from sfc.personas.sports.transfer.service import TransferPersona
    persona = TransferPersona()
    insight = await persona.generate_insight(state.get("task_payload", {}))
    return {
        "sports_persona_insight": insight.model_dump(),
        "pipeline_stage": "transfer_persona_complete",
    }


async def tactical_persona_node(state: dict[str, Any]) -> dict[str, Any]:
    from sfc.personas.sports.tactical.service import TacticalPersona
    persona = TacticalPersona()
    insight = await persona.generate_insight(state.get("task_payload", {}))
    return {
        "sports_persona_insight": insight.model_dump(),
        "pipeline_stage": "tactical_persona_complete",
    }


async def opponent_analysis_persona_node(state: dict[str, Any]) -> dict[str, Any]:
    from sfc.personas.sports.opponent_analysis.service import OpponentAnalysisPersona
    persona = OpponentAnalysisPersona()
    insight = await persona.generate_insight(state.get("task_payload", {}))
    return {
        "sports_persona_insight": insight.model_dump(),
        "pipeline_stage": "opponent_analysis_persona_complete",
    }


async def fan_sentiment_persona_node(state: dict[str, Any]) -> dict[str, Any]:
    from sfc.personas.sports.fan_sentiment.service import FanSentimentPersona
    persona = FanSentimentPersona()
    insight = await persona.generate_insight(state.get("task_payload", {}))
    return {
        "sports_persona_insight": insight.model_dump(),
        "pipeline_stage": "fan_sentiment_persona_complete",
    }


async def journalist_intelligence_persona_node(state: dict[str, Any]) -> dict[str, Any]:
    from sfc.personas.sports.journalist_intelligence.service import JournalistIntelligencePersona
    persona = JournalistIntelligencePersona()
    insight = await persona.generate_insight(state.get("task_payload", {}))
    return {
        "sports_persona_insight": insight.model_dump(),
        "pipeline_stage": "journalist_intelligence_persona_complete",
    }


async def injury_intelligence_persona_node(state: dict[str, Any]) -> dict[str, Any]:
    from sfc.personas.sports.injury_intelligence.service import InjuryIntelligencePersona
    persona = InjuryIntelligencePersona()
    insight = await persona.generate_insight(state.get("task_payload", {}))
    return {
        "sports_persona_insight": insight.model_dump(),
        "pipeline_stage": "injury_intelligence_persona_complete",
    }


async def performance_science_persona_node(state: dict[str, Any]) -> dict[str, Any]:
    from sfc.personas.sports.performance_science.service import PerformanceSciencePersona
    persona = PerformanceSciencePersona()
    insight = await persona.generate_insight(state.get("task_payload", {}))
    return {
        "sports_persona_insight": insight.model_dump(),
        "pipeline_stage": "performance_science_persona_complete",
    }


async def referee_analysis_persona_node(state: dict[str, Any]) -> dict[str, Any]:
    from sfc.personas.sports.referee_analysis.service import RefereeAnalysisPersona
    persona = RefereeAnalysisPersona()
    insight = await persona.generate_insight(state.get("task_payload", {}))
    return {
        "sports_persona_insight": insight.model_dump(),
        "pipeline_stage": "referee_analysis_persona_complete",
    }
