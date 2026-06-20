"""Shared types and events for the war rooms subsystem."""

from __future__ import annotations

from sfc.war_rooms.shared.types import (
    WarRoomAllocation,
    WarRoomHealth,
    WarRoomMetrics,
    WarRoomPriority,
    WarRoomState,
    WarRoomStatus,
    WarRoomType,
)
from sfc.war_rooms.shared.events import (
    CrisisTriggered,
    MatchTriggered,
    PriorityChanged,
    ResourceAllocated,
    TransferWindowTriggered,
    WarRoomActivated,
    WarRoomClosed,
    WarRoomDeactivated,
    WarRoomEscalated,
    WorldCupTriggered,
)

__all__ = [
    "WarRoomAllocation",
    "WarRoomHealth",
    "WarRoomMetrics",
    "WarRoomPriority",
    "WarRoomState",
    "WarRoomStatus",
    "WarRoomType",
    "CrisisTriggered",
    "MatchTriggered",
    "PriorityChanged",
    "ResourceAllocated",
    "TransferWindowTriggered",
    "WarRoomActivated",
    "WarRoomClosed",
    "WarRoomDeactivated",
    "WarRoomEscalated",
    "WorldCupTriggered",
]
