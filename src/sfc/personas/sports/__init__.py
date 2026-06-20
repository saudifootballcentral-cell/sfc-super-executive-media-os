"""Sports Intelligence Personas — SFC Super Executive Media OS."""
from __future__ import annotations

from sfc.personas.sports.national_team.service import NationalTeamPersona
from sfc.personas.sports.spl.service import SPLPersona
from sfc.personas.sports.world_cup.service import WorldCupPersona
from sfc.personas.sports.afc.service import AFCPersona
from sfc.personas.sports.fifa.service import FIFAPersona
from sfc.personas.sports.transfer.service import TransferPersona
from sfc.personas.sports.tactical.service import TacticalPersona
from sfc.personas.sports.opponent_analysis.service import OpponentAnalysisPersona
from sfc.personas.sports.fan_sentiment.service import FanSentimentPersona
from sfc.personas.sports.journalist_intelligence.service import JournalistIntelligencePersona
from sfc.personas.sports.injury_intelligence.service import InjuryIntelligencePersona
from sfc.personas.sports.performance_science.service import PerformanceSciencePersona
from sfc.personas.sports.referee_analysis.service import RefereeAnalysisPersona

_ALL_SPORTS_PERSONAS = [
    NationalTeamPersona,
    SPLPersona,
    WorldCupPersona,
    AFCPersona,
    FIFAPersona,
    TransferPersona,
    TacticalPersona,
    OpponentAnalysisPersona,
    FanSentimentPersona,
    JournalistIntelligencePersona,
    InjuryIntelligencePersona,
    PerformanceSciencePersona,
    RefereeAnalysisPersona,
]


def register_sports_personas(registry) -> int:
    """Register all 13 sports personas with the provided PersonaRegistry.

    Returns count of newly registered personas.
    """
    count = 0
    for cls in _ALL_SPORTS_PERSONAS:
        persona = cls()
        existing = registry.get(persona.PERSONA_ID)
        if existing is None:
            registry.register(persona.profile)
            count += 1
    return count


__all__ = [
    "NationalTeamPersona",
    "SPLPersona",
    "WorldCupPersona",
    "AFCPersona",
    "FIFAPersona",
    "TransferPersona",
    "TacticalPersona",
    "OpponentAnalysisPersona",
    "FanSentimentPersona",
    "JournalistIntelligencePersona",
    "InjuryIntelligencePersona",
    "PerformanceSciencePersona",
    "RefereeAnalysisPersona",
    "register_sports_personas",
]
