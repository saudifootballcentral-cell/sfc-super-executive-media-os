"""Transfer Window War Room — tracks every Saudi Pro League transfer in real time."""

from __future__ import annotations

from typing import Any

from core.models import WarRoom
from war_rooms.base import BaseWarRoom


class TransferWindowWarRoom(BaseWarRoom):
    """Activated during transfer windows. Monitors rumors, breaks news, drives engagement."""

    war_room = WarRoom.TRANSFER_WINDOW

    def _on_activate(self, context: dict[str, Any]) -> None:
        self.window_context = context
        self.rumors: list[dict[str, Any]] = []
        self.confirmed: list[dict[str, Any]] = []
        self.record("window_opened", context)

    def _on_deactivate(self, summary: dict[str, Any]) -> None:
        self.record("window_closed", summary)

    def add_rumor(self, player: str, from_club: str, to_club: str, reliability: float, source: str) -> dict[str, Any]:
        rumor = {
            "player": player,
            "from_club": from_club,
            "to_club": to_club,
            "reliability": reliability,
            "source": source,
            "label": "RUMOR",
            "confirmed": False,
        }
        self.rumors.append(rumor)
        self.record("rumor_added", rumor)
        self.logger.info("[TransferWindow] RUMOR: %s → %s (reliability %.0f%%)", player, to_club, reliability)
        return rumor

    def confirm_transfer(self, player: str, to_club: str, fee_eur: float | None = None) -> dict[str, Any]:
        transfer = {
            "player": player,
            "to_club": to_club,
            "fee_eur": fee_eur,
            "confirmed": True,
            "label": "CONFIRMED",
        }
        self.confirmed.append(transfer)
        self.rumors = [r for r in self.rumors if r["player"] != player]
        self.record("transfer_confirmed", transfer)
        self.logger.info("[TransferWindow] CONFIRMED: %s → %s", player, to_club)
        return transfer

    def get_transfer_board(self) -> dict[str, Any]:
        return {
            "rumors": self.rumors,
            "confirmed": self.confirmed,
            "rumor_count": len(self.rumors),
            "confirmed_count": len(self.confirmed),
        }
