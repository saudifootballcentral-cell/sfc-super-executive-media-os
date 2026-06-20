"""World Cup War Room — maximum intensity, all divisions, P1 priority."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, TYPE_CHECKING

from sfc.war_rooms.deactivation.models import ClosureReport
from sfc.war_rooms.shared.types import (
    WarRoomHealth,
    WarRoomPriority,
    WarRoomState,
    WarRoomType,
)
from sfc.war_rooms.world_cup.models import (
    NationalTeamMonitor,
    WorldCupBrief,
    WorldCupPhase,
)

if TYPE_CHECKING:
    from sfc.war_rooms.registry.service import WarRoomRegistry

logger = logging.getLogger("sfc.war_rooms.world_cup")

_PHASE_CONTENT_TEMPLATES = {
    WorldCupPhase.PRE_TOURNAMENT: ["squad_analysis", "fixture_preview", "opponent_profiles", "sponsor_kickoff"],
    WorldCupPhase.GROUP_STAGE: ["match_preview", "live_coverage", "match_report", "group_standings"],
    WorldCupPhase.KNOCKOUT: ["bracket_update", "match_preview", "live_coverage", "match_report"],
    WorldCupPhase.FINAL_WEEK: ["daily_coverage", "final_preview", "legacy_piece", "sponsor_finale"],
    WorldCupPhase.POST_TOURNAMENT: ["tournament_review", "player_awards", "legacy_narrative"],
}


class WorldCupWarRoom:
    """World Cup War Room — maximum intensity, all divisions, P1 priority."""

    war_room_type = WarRoomType.WORLD_CUP
    default_priority = WarRoomPriority.P1_CRITICAL
    MONITORING_INTERVAL_MINUTES = 15

    def __init__(self, registry: "WarRoomRegistry") -> None:
        self._registry = registry
        self._phase = WorldCupPhase.PRE_TOURNAMENT
        self._team_monitor = NationalTeamMonitor()
        self._state: WarRoomState | None = None

    async def activate(self, tournament_metadata: dict[str, Any] | None = None) -> WarRoomState:
        """Activate the World Cup War Room."""
        if tournament_metadata is None:
            tournament_metadata = {}

        existing = self._registry.get_by_type(WarRoomType.WORLD_CUP)
        if existing is not None:
            self._state = existing
            return existing

        state = self._registry.activate(
            WarRoomType.WORLD_CUP,
            metadata={
                "phase": self._phase,
                "monitoring_interval_minutes": self.MONITORING_INTERVAL_MINUTES,
                **tournament_metadata,
            },
        )
        self._state = state
        logger.info("[WorldCup] Activated — phase: %s", self._phase)
        return state

    async def create_daily_brief(
        self, phase: WorldCupPhase, team_monitor: NationalTeamMonitor
    ) -> WorldCupBrief:
        """Daily intelligence + content brief for World Cup operations."""
        narrative_opportunities = await self.detect_narrative_opportunities(
            WorldCupBrief(
                phase=phase,
                national_team=team_monitor,
            )
        )
        sponsor_activations = await self.create_sponsor_activations(phase)
        content_templates = _PHASE_CONTENT_TEMPLATES.get(phase, [])
        daily_content_plan = [
            {"content_type": ct, "phase": phase, "team": team_monitor.team, "priority": "high"}
            for ct in content_templates
        ]
        executive_report = (
            f"World Cup Daily Brief — Phase: {phase.value.replace('_', ' ').title()}. "
            f"Monitoring {team_monitor.team}. "
            f"{len(narrative_opportunities)} narrative opportunities identified. "
            f"{len(sponsor_activations)} sponsor activations planned. "
            f"Content plan: {len(daily_content_plan)} items. "
            f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}."
        )
        return WorldCupBrief(
            phase=phase,
            national_team=team_monitor,
            narrative_opportunities=narrative_opportunities,
            sponsor_activations=sponsor_activations,
            daily_content_plan=daily_content_plan,
            executive_report=executive_report,
        )

    async def monitor_national_team(self, match_data: dict[str, Any] | None = None) -> NationalTeamMonitor:
        """Update national team monitoring state."""
        if match_data is None:
            match_data = {}

        if match_data.get("result"):
            self._team_monitor.results.append(match_data["result"])
        if match_data.get("next_match"):
            self._team_monitor.next_match = match_data["next_match"]
        if match_data.get("squad"):
            self._team_monitor.squad = match_data["squad"]
        if match_data.get("phase"):
            self._team_monitor.current_phase = WorldCupPhase(match_data["phase"])

        # Generate key narratives
        narratives = []
        if self._team_monitor.results:
            last_result = self._team_monitor.results[-1]
            narratives.append(f"Latest result: {last_result}")
        narratives.append(f"{self._team_monitor.team} World Cup journey — all eyes on the Green Falcons.")
        self._team_monitor.key_narratives = narratives

        return self._team_monitor

    async def create_opponent_report(
        self, opponent: str, match_context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Full opponent analysis: style, key players, historical record vs Saudi Arabia."""
        if match_context is None:
            match_context = {}
        return {
            "opponent": opponent,
            "match_context": match_context,
            "playing_style": f"{opponent} tactical style analysis — intelligence update pending",
            "key_players": match_context.get("key_players", []),
            "historical_record_vs_saudi": {
                "played": match_context.get("historical_played", 0),
                "saudi_wins": match_context.get("saudi_wins", 0),
                "draws": match_context.get("draws", 0),
                "opponent_wins": match_context.get("opponent_wins", 0),
            },
            "threat_assessment": f"Full threat assessment for {opponent} to be completed 48h before match.",
            "tactical_recommendations": [
                f"Nullify {opponent}'s key players through disciplined defensive shape.",
                "Exploit transition opportunities.",
            ],
            "generated_at": datetime.utcnow().isoformat(),
        }

    async def detect_narrative_opportunities(self, brief: WorldCupBrief) -> list[str]:
        """Identify content narrative opportunities from current World Cup context."""
        opportunities = [
            f"{brief.national_team.team} — Pride of the Nation: capturing the World Cup journey.",
            "Historic moments: documenting Saudi football on the global stage.",
            "Fan stories: voices from the Kingdom.",
            f"Phase focus: {brief.phase.value.replace('_', ' ').title()} insights and analysis.",
        ]
        if brief.national_team.next_match:
            opponent = brief.national_team.next_match.get("opponent", "next opponent")
            opportunities.append(f"Match preview: {brief.national_team.team} vs {opponent}")
        return opportunities

    async def create_sponsor_activations(self, phase: WorldCupPhase) -> list[dict[str, Any]]:
        """Generate sponsor activation opportunities by phase."""
        base_activations = [
            {"activation": "match_preview_sponsor_slot", "phase": phase, "format": "digital_banner"},
            {"activation": "player_spotlight_sponsor", "phase": phase, "format": "social_post"},
        ]
        phase_specific = {
            WorldCupPhase.PRE_TOURNAMENT: [
                {"activation": "squad_announcement_sponsor", "phase": phase, "format": "video"},
            ],
            WorldCupPhase.GROUP_STAGE: [
                {"activation": "live_match_sponsor_ticker", "phase": phase, "format": "live_ticker"},
            ],
            WorldCupPhase.FINAL_WEEK: [
                {"activation": "final_week_campaign", "phase": phase, "format": "full_campaign"},
            ],
            WorldCupPhase.POST_TOURNAMENT: [
                {"activation": "legacy_content_sponsor", "phase": phase, "format": "documentary"},
            ],
        }
        return base_activations + phase_specific.get(phase, [])

    async def deactivate(self) -> ClosureReport:
        """Close the World Cup War Room."""
        from sfc.war_rooms.deactivation.service import DeactivationEngine
        engine = DeactivationEngine(self._registry)
        state = self._state or self._registry.get_by_type(WarRoomType.WORLD_CUP)
        if state is None:
            raise ValueError("No active World Cup war room to deactivate")
        return await engine.deactivate(state.war_room_id, reason="tournament_concluded")

    def health_check(self) -> WarRoomHealth:
        """Return health status."""
        try:
            state = self._state or self._registry.get_by_type(WarRoomType.WORLD_CUP)
            if state is None:
                return WarRoomHealth(
                    war_room_id="none",
                    status="inactive",
                    health_score=100.0,
                    warnings=["No active World Cup war room"],
                )
            return WarRoomHealth(
                war_room_id=state.war_room_id,
                status=state.status,
                health_score=state.health_score,
                warnings=[],
            )
        except Exception as exc:
            return WarRoomHealth(
                war_room_id="error",
                status="unhealthy",
                health_score=0.0,
                warnings=[str(exc)],
            )
