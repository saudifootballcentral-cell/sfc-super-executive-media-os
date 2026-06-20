"""War Room event types extending the base event bus."""

from __future__ import annotations

from sfc.events.types import BaseEvent


class WarRoomActivated(BaseEvent):
    event_type: str = "war_room_activated"
    # payload contains: war_room_id, war_room_type, priority


class WarRoomDeactivated(BaseEvent):
    event_type: str = "war_room_deactivated"


class WarRoomEscalated(BaseEvent):
    event_type: str = "war_room_escalated"


class ResourceAllocated(BaseEvent):
    event_type: str = "resource_allocated"


class PriorityChanged(BaseEvent):
    event_type: str = "priority_changed"


class CrisisTriggered(BaseEvent):
    event_type: str = "crisis_triggered"


class MatchTriggered(BaseEvent):
    event_type: str = "match_triggered"


class WorldCupTriggered(BaseEvent):
    event_type: str = "world_cup_triggered"


class TransferWindowTriggered(BaseEvent):
    event_type: str = "transfer_window_triggered"


class WarRoomClosed(BaseEvent):
    event_type: str = "war_room_closed"
