"""World Cup War Room — dedicated command center for FIFA World Cup 2034 coverage."""

from __future__ import annotations

from typing import Any

from core.models import WarRoom
from war_rooms.base import BaseWarRoom


class WorldCupWarRoom(BaseWarRoom):
    """World Cup 2034 coverage coordination center.

    Saudi Arabia hosts the 2034 FIFA World Cup — maximum priority event.
    Coordinates across all divisions and platforms for comprehensive coverage.
    """

    war_room = WarRoom.WORLD_CUP

    def _on_activate(self, context: dict[str, Any]) -> None:
        self.tournament_context = context
        self.covered_matches: list[dict[str, Any]] = []
        self.storylines: list[dict[str, Any]] = []
        self.record("world_cup_coverage_started", context)
        self.logger.info("[WorldCup] Coverage activated for: %s", context.get("phase", "Group Stage"))

    def _on_deactivate(self, summary: dict[str, Any]) -> None:
        self.record("world_cup_coverage_ended", summary)

    def add_storyline(self, title: str, priority: str, nations_involved: list[str]) -> dict[str, Any]:
        storyline = {
            "title": title,
            "priority": priority,
            "nations_involved": nations_involved,
            "status": "active",
        }
        self.storylines.append(storyline)
        self.record("storyline_added", storyline)
        return storyline

    def track_saudi_national_team(self, event: str, details: dict[str, Any]) -> None:
        self.record(f"ksa_national_team:{event}", details)
        self.logger.info("[WorldCup] KSA National Team: %s", event)

    def get_coverage_summary(self) -> dict[str, Any]:
        return {
            "matches_covered": len(self.covered_matches),
            "active_storylines": len([s for s in self.storylines if s["status"] == "active"]),
            "log_entries": len(self.log),
        }
