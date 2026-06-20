"""Transfer Window War Room — market intelligence and rumor management."""

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
from sfc.war_rooms.transfer_window.models import (
    TransferItem,
    TransferStatus,
    TransferTracker,
)

if TYPE_CHECKING:
    from sfc.war_rooms.registry.service import WarRoomRegistry

logger = logging.getLogger("sfc.war_rooms.transfer_window")

_SAUDI_CLUBS = {
    "al nassr", "al hilal", "al ittihad", "al ahli", "al qadsiah",
    "al taawoun", "al fateh", "al shabab", "al wehda", "al feiha",
}


def _is_saudi_related(transfer_data: dict[str, Any]) -> bool:
    """Check if transfer involves a Saudi club."""
    from_club = transfer_data.get("from_club", "").lower()
    to_club = transfer_data.get("to_club", "").lower()
    player_nationality = transfer_data.get("nationality", "").lower()
    return (
        any(club in from_club for club in _SAUDI_CLUBS)
        or any(club in to_club for club in _SAUDI_CLUBS)
        or player_nationality == "saudi"
    )


class TransferWindowWarRoom:
    """Transfer Window War Room — market intelligence and rumor management."""

    war_room_type = WarRoomType.TRANSFER_WINDOW
    default_priority = WarRoomPriority.P3_MEDIUM

    def __init__(self, registry: "WarRoomRegistry") -> None:
        self._registry = registry
        self._tracker = TransferTracker()
        self._state: WarRoomState | None = None

    async def activate(self, window_type: str = "summer") -> WarRoomState:
        """Activate the Transfer Window War Room."""
        self._tracker = TransferTracker(window_type=window_type)

        existing = self._registry.get_by_type(WarRoomType.TRANSFER_WINDOW)
        if existing is not None:
            self._state = existing
            return existing

        state = self._registry.activate(
            WarRoomType.TRANSFER_WINDOW,
            metadata={"window_type": window_type},
        )
        self._state = state
        logger.info("[TransferWindow] Activated — window type: %s", window_type)
        return state

    async def ingest_transfer(self, transfer_data: dict[str, Any]) -> TransferItem:
        """Ingest a new transfer report and classify it."""
        status = await self.classify_transfer(transfer_data)
        is_saudi = _is_saudi_related(transfer_data)
        confidence = self._compute_confidence(transfer_data, status)

        item = TransferItem(
            player=transfer_data.get("player", "Unknown"),
            from_club=transfer_data.get("from_club", "Unknown"),
            to_club=transfer_data.get("to_club", "Unknown"),
            status=status,
            fee_estimate_m_eur=transfer_data.get("fee_estimate_m_eur"),
            sources=transfer_data.get("sources", []),
            confidence_score=confidence,
            is_saudi_related=is_saudi,
            notes=transfer_data.get("notes", ""),
        )

        self._tracker.items.append(item)
        self._tracker.total_tracked += 1
        if is_saudi:
            self._tracker.saudi_related_count += 1
        if status == TransferStatus.OFFICIAL_CONFIRMATION:
            self._tracker.confirmed_count += 1
        if status in (TransferStatus.RUMOR, TransferStatus.STRONG_RUMOR):
            self._tracker.rumor_count += 1
        self._tracker.last_updated = datetime.utcnow()

        logger.info("[TransferWindow] Ingested transfer: %s → %s (%s) status=%s",
                    item.player, item.to_club, item.from_club, status)
        return item

    async def update_transfer_status(
        self,
        transfer_id: str,
        new_status: TransferStatus,
        sources: list[str] | None = None,
    ) -> TransferItem:
        """Update status when new information arrives."""
        for item in self._tracker.items:
            if item.transfer_id == transfer_id:
                item.status = new_status
                if sources:
                    item.sources.extend(sources)
                item.last_updated = datetime.utcnow()
                item.confidence_score = self._compute_confidence(
                    {"sources": item.sources}, new_status
                )
                return item
        raise ValueError(f"Transfer not found: {transfer_id}")

    async def classify_transfer(self, transfer_data: dict[str, Any]) -> TransferStatus:
        """Classify transfer status from available evidence.

        Rules:
        - 1 source + no detail → RUMOR
        - 2 sources + journalist confirmation → STRONG_RUMOR
        - club sources + fee mentioned → ADVANCED_NEGOTIATION
        - player/agent confirmation → VERBAL_AGREEMENT
        - official club announcement → OFFICIAL_CONFIRMATION
        """
        sources = transfer_data.get("sources", [])
        fee_mentioned = transfer_data.get("fee_estimate_m_eur") is not None
        official_announcement = transfer_data.get("official_announcement", False)
        player_confirmed = transfer_data.get("player_confirmed", False)
        agent_confirmed = transfer_data.get("agent_confirmed", False)
        club_sources = transfer_data.get("club_sources", False)
        journalist_count = transfer_data.get("journalist_count", 0)

        if official_announcement:
            return TransferStatus.OFFICIAL_CONFIRMATION
        if player_confirmed or agent_confirmed:
            return TransferStatus.VERBAL_AGREEMENT
        if club_sources and fee_mentioned:
            return TransferStatus.ADVANCED_NEGOTIATION
        if len(sources) >= 2 or journalist_count >= 2:
            return TransferStatus.STRONG_RUMOR
        return TransferStatus.RUMOR

    async def create_transfer_brief(
        self, items: list[TransferItem] | None = None
    ) -> dict[str, Any]:
        """Summary brief of current transfer window activity."""
        target_items = items or self._tracker.items
        saudi_items = [i for i in target_items if i.is_saudi_related]
        confirmed = [i for i in target_items if i.status == TransferStatus.OFFICIAL_CONFIRMATION]
        return {
            "window_type": self._tracker.window_type,
            "window_open": self._tracker.window_open,
            "total_tracked": len(target_items),
            "items": [
                {
                    "transfer_id": i.transfer_id,
                    "player": i.player,
                    "from_club": i.from_club,
                    "to_club": i.to_club,
                    "status": i.status,
                    "confidence_score": i.confidence_score,
                    "is_saudi_related": i.is_saudi_related,
                }
                for i in target_items
            ],
            "saudi_related_count": len(saudi_items),
            "confirmed_count": len(confirmed),
            "rumor_count": sum(1 for i in target_items if i.status in (TransferStatus.RUMOR, TransferStatus.STRONG_RUMOR)),
            "generated_at": datetime.utcnow().isoformat(),
        }

    async def analyze_squad_impact(self, transfer: TransferItem) -> dict[str, Any]:
        """Analyze impact on Saudi club's squad if transfer completes."""
        impact = {
            "transfer_id": transfer.transfer_id,
            "player": transfer.player,
            "from_club": transfer.from_club,
            "to_club": transfer.to_club,
            "status": transfer.status,
            "is_saudi_related": transfer.is_saudi_related,
            "impact_assessment": "Detailed squad impact analysis requires roster data.",
            "financial_impact": (
                f"Estimated fee: €{transfer.fee_estimate_m_eur}M"
                if transfer.fee_estimate_m_eur else "Fee not disclosed"
            ),
            "squad_position_effect": "Position analysis pending squad data.",
            "rating": "medium",
        }
        if transfer.is_saudi_related:
            impact["saudi_league_significance"] = (
                f"Transfer directly impacts Saudi Pro League. {transfer.player} moving "
                f"{'to' if transfer.to_club.lower() in str(_SAUDI_CLUBS) else 'from'} Saudi football."
            )
        return impact

    async def create_executive_alert(self, transfer: TransferItem) -> str:
        """Generate executive alert for significant transfer news."""
        urgency = {
            TransferStatus.OFFICIAL_CONFIRMATION: "CONFIRMED",
            TransferStatus.VERBAL_AGREEMENT: "BREAKING",
            TransferStatus.ADVANCED_NEGOTIATION: "ADVANCED",
            TransferStatus.STRONG_RUMOR: "DEVELOPING",
            TransferStatus.RUMOR: "RUMOR",
        }
        label = urgency.get(transfer.status, "UPDATE")
        alert = (
            f"[TRANSFER ALERT — {label}] {transfer.player} ({transfer.from_club} → {transfer.to_club}). "
            f"Status: {transfer.status.value.replace('_', ' ').title()}. "
            f"Confidence: {transfer.confidence_score:.0f}%. "
        )
        if transfer.fee_estimate_m_eur:
            alert += f"Estimated fee: €{transfer.fee_estimate_m_eur}M. "
        if transfer.is_saudi_related:
            alert += "SAUDI RELATED — prioritize coverage. "
        if transfer.status in (TransferStatus.RUMOR, TransferStatus.STRONG_RUMOR):
            alert += "Note: Unconfirmed report — include disclaimer in all coverage."
        return alert

    def get_tracker(self) -> TransferTracker:
        return self._tracker

    async def deactivate(self) -> ClosureReport:
        """Close the Transfer Window War Room."""
        from sfc.war_rooms.deactivation.service import DeactivationEngine
        engine = DeactivationEngine(self._registry)
        state = self._state or self._registry.get_by_type(WarRoomType.TRANSFER_WINDOW)
        if state is None:
            raise ValueError("No active Transfer Window war room to deactivate")
        return await engine.deactivate(state.war_room_id, reason="window_closed")

    def health_check(self) -> WarRoomHealth:
        """Return health status."""
        try:
            state = self._state or self._registry.get_by_type(WarRoomType.TRANSFER_WINDOW)
            if state is None:
                return WarRoomHealth(
                    war_room_id="none",
                    status="inactive",
                    health_score=100.0,
                    warnings=["No active Transfer Window war room"],
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

    def _compute_confidence(
        self, transfer_data: dict[str, Any], status: TransferStatus
    ) -> float:
        """Compute confidence score from status and source count."""
        base = {
            TransferStatus.RUMOR: 30.0,
            TransferStatus.STRONG_RUMOR: 55.0,
            TransferStatus.ADVANCED_NEGOTIATION: 70.0,
            TransferStatus.VERBAL_AGREEMENT: 85.0,
            TransferStatus.OFFICIAL_CONFIRMATION: 99.0,
        }
        score = base.get(status, 50.0)
        source_bonus = min(len(transfer_data.get("sources", [])) * 2.0, 10.0)
        return min(99.0, score + source_bonus)
