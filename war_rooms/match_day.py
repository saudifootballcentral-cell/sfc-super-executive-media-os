"""Match Day War Room — real-time coordination during live Saudi football matches."""

from __future__ import annotations

from typing import Any

from core.models import EventType, WarRoom
from war_rooms.base import BaseWarRoom


class MatchDayWarRoom(BaseWarRoom):
    """Activated when a match starts. Coordinates live content across all platforms.

    Covers: pre-match, live updates, goal moments, half-time, full-time.
    """

    war_room = WarRoom.MATCH_DAY

    def _on_activate(self, context: dict[str, Any]) -> None:
        self.match_context = context
        self.goals: list[dict[str, Any]] = []
        self.record("match_started", context)

    def _on_deactivate(self, summary: dict[str, Any]) -> None:
        self.record("match_ended", summary)

    def record_goal(
        self,
        scorer: str,
        team: str,
        minute: int,
        home_score: int,
        away_score: int,
    ) -> dict[str, Any]:
        goal = {
            "scorer": scorer,
            "team": team,
            "minute": minute,
            "score": f"{home_score}-{away_score}",
        }
        self.goals.append(goal)
        self.record("goal_scored", goal)
        self.logger.info("[MatchDay] GOAL! %s (%s) — %d' | Score: %s", scorer, team, minute, goal["score"])
        return goal

    def record_half_time(self, home_score: int, away_score: int) -> None:
        self.record("half_time", {"home_score": home_score, "away_score": away_score})

    def get_match_summary(self) -> dict[str, Any]:
        return {
            "context": getattr(self, "match_context", {}),
            "goals": self.goals,
            "log": self.get_log(),
        }
