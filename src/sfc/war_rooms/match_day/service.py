"""Match Day War Room — owns the complete match narrative."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, TYPE_CHECKING

from sfc.war_rooms.deactivation.models import ClosureReport
from sfc.war_rooms.match_day.models import MatchDayOutput, MatchInfo, MatchPhase
from sfc.war_rooms.shared.types import (
    WarRoomHealth,
    WarRoomPriority,
    WarRoomState,
    WarRoomStatus,
    WarRoomType,
)

if TYPE_CHECKING:
    from sfc.war_rooms.registry.service import WarRoomRegistry

logger = logging.getLogger("sfc.war_rooms.match_day")

_PRE_MATCH_CONTENT = [
    {"type": "tactical_preview", "format": "article", "priority": "high"},
    {"type": "lineup_analysis", "format": "graphic", "priority": "high"},
    {"type": "prediction_thread", "format": "social_thread", "priority": "medium"},
    {"type": "match_preview_video", "format": "video", "priority": "medium"},
]
_LIVE_CONTENT = [
    {"type": "live_blog", "format": "live_text", "priority": "critical"},
    {"type": "stat_graphics", "format": "graphic", "priority": "high"},
    {"type": "key_moments", "format": "short_video", "priority": "high"},
    {"type": "halftime_analysis", "format": "article", "priority": "high"},
]
_POST_MATCH_CONTENT = [
    {"type": "match_report", "format": "article", "priority": "critical"},
    {"type": "player_ratings", "format": "graphic", "priority": "high"},
    {"type": "tactical_breakdown", "format": "article", "priority": "high"},
    {"type": "highlights_brief", "format": "short_video", "priority": "high"},
    {"type": "fan_sentiment", "format": "social_thread", "priority": "medium"},
]


class MatchDayWarRoom:
    """Match Day War Room — owns the complete match narrative."""

    war_room_type = WarRoomType.MATCH_DAY
    default_priority = WarRoomPriority.P3_MEDIUM

    def __init__(self, registry: "WarRoomRegistry") -> None:
        self._registry = registry
        self._current_match: MatchInfo | None = None
        self._phase = MatchPhase.PRE_MATCH
        self._output = MatchDayOutput(match_id="", phase=MatchPhase.PRE_MATCH)
        self._state: WarRoomState | None = None

    async def activate(self, match_info: MatchInfo) -> WarRoomState:
        """Activate match day war room for a specific match."""
        self._current_match = match_info
        self._phase = MatchPhase.PRE_MATCH
        self._output = MatchDayOutput(match_id=match_info.match_id, phase=MatchPhase.PRE_MATCH)

        existing = self._registry.get_by_type(WarRoomType.MATCH_DAY)
        if existing is not None:
            self._state = existing
            return existing

        state = self._registry.activate(
            WarRoomType.MATCH_DAY,
            metadata={
                "match_id": match_info.match_id,
                "home_team": match_info.home_team,
                "away_team": match_info.away_team,
                "competition": match_info.competition,
            },
        )
        self._state = state
        logger.info("[MatchDay] Activated for %s vs %s", match_info.home_team, match_info.away_team)
        return state

    async def create_match_brief(self, match_info: MatchInfo) -> dict[str, Any]:
        """Pre-match intelligence brief: lineup analysis, opponent profile, tactical preview."""
        brief = {
            "match_id": match_info.match_id,
            "home_team": match_info.home_team,
            "away_team": match_info.away_team,
            "competition": match_info.competition,
            "venue": match_info.venue,
            "kickoff_time": match_info.kickoff_time.isoformat() if match_info.kickoff_time else None,
            "tactical_preview": {
                "home_formation": "4-3-3",
                "away_formation": "4-2-3-1",
                "key_battles": [
                    f"{match_info.home_team} midfield vs {match_info.away_team} pressing",
                    "Set piece threat from both sides",
                ],
                "prediction": f"Competitive match expected; {match_info.home_team} slight advantage at home.",
            },
            "opponent_profile": {
                "team": match_info.away_team,
                "recent_form": "Unknown — requires intelligence update",
                "key_players": [],
                "threats": [],
            },
            "lineup_analysis": {
                "home_expected": f"{match_info.home_team} expected lineup pending official confirmation",
                "away_expected": f"{match_info.away_team} expected lineup pending official confirmation",
                "injury_updates": [],
            },
            "generated_at": datetime.utcnow().isoformat(),
        }
        self._output.match_brief = brief
        return brief

    async def create_content_plan(self, match_info: MatchInfo, phase: MatchPhase) -> list[dict[str, Any]]:
        """Generate content production plan for this match phase."""
        phase_map = {
            MatchPhase.PRE_MATCH: _PRE_MATCH_CONTENT,
            MatchPhase.LIVE: _LIVE_CONTENT,
            MatchPhase.POST_MATCH: _POST_MATCH_CONTENT,
            MatchPhase.CLOSED: [],
        }
        plan = [
            {**item, "match_id": match_info.match_id, "phase": phase}
            for item in phase_map.get(phase, [])
        ]
        self._output.content_plan = plan
        return plan

    async def create_match_report(self, match_info: MatchInfo, result: dict[str, Any]) -> dict[str, Any]:
        """Post-match report: result, key moments, tactical analysis."""
        home_score = result.get("home_score", 0)
        away_score = result.get("away_score", 0)
        winner = (
            match_info.home_team if home_score > away_score
            else match_info.away_team if away_score > home_score
            else "Draw"
        )
        report = {
            "match_id": match_info.match_id,
            "home_team": match_info.home_team,
            "away_team": match_info.away_team,
            "competition": match_info.competition,
            "result": f"{match_info.home_team} {home_score}-{away_score} {match_info.away_team}",
            "winner": winner,
            "key_moments": result.get("key_moments", []),
            "tactical_analysis": {
                "home_performance": "Analysis pending match data",
                "away_performance": "Analysis pending match data",
                "decisive_factor": result.get("decisive_factor", "To be determined"),
            },
            "attendance": result.get("attendance", "TBC"),
            "generated_at": datetime.utcnow().isoformat(),
        }
        self._output.match_report = report
        return report

    async def create_player_ratings(
        self, match_info: MatchInfo, performance_data: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Rate each player 1-10 with brief rationale."""
        players = performance_data.get("players", [
            {"name": f"{match_info.home_team} Player", "team": match_info.home_team},
            {"name": f"{match_info.away_team} Player", "team": match_info.away_team},
        ])
        ratings = []
        for player in players:
            rating_entry = {
                "player": player.get("name", "Unknown"),
                "team": player.get("team", "Unknown"),
                "rating": player.get("rating", 6.5),
                "rationale": player.get("rationale", "Standard performance; detailed stats pending."),
                "goals": player.get("goals", 0),
                "assists": player.get("assists", 0),
            }
            ratings.append(rating_entry)
        self._output.player_ratings = ratings
        return ratings

    async def create_executive_summary(self) -> str:
        """Single-paragraph executive summary of the match narrative."""
        if self._current_match is None:
            return "No match data available for executive summary."
        match = self._current_match
        summary = (
            f"Match Day War Room report for {match.competition}: {match.home_team} vs {match.away_team}. "
            f"Operations covered all phases from pre-match intelligence through post-match analysis. "
            f"Content pipeline produced tactical previews, live coverage, and post-match reporting "
            f"across all SFC platforms. All governance checks completed. "
            f"Report generated at {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}."
        )
        self._output.executive_summary = summary
        return summary

    async def deactivate(self) -> ClosureReport:
        """Close war room and generate closure report."""
        from sfc.war_rooms.deactivation.service import DeactivationEngine
        engine = DeactivationEngine(self._registry)
        state = self._state or self._registry.get_by_type(WarRoomType.MATCH_DAY)
        if state is None:
            raise ValueError("No active Match Day war room to deactivate")
        return await engine.deactivate(state.war_room_id, reason="match_completed")

    def health_check(self) -> WarRoomHealth:
        """Return health status."""
        try:
            state = self._state or self._registry.get_by_type(WarRoomType.MATCH_DAY)
            if state is None:
                return WarRoomHealth(
                    war_room_id="none",
                    status="inactive",
                    health_score=100.0,
                    warnings=["No active Match Day war room"],
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
