"""Registry models for War Room definitions."""

from __future__ import annotations

from pydantic import BaseModel

from sfc.war_rooms.shared.types import WarRoomPriority, WarRoomType


class WarRoomDefinition(BaseModel):
    """Static configuration for a war room type."""

    war_room_id: str
    name: str
    war_room_type: WarRoomType
    default_priority: WarRoomPriority
    default_divisions: list[str]
    activation_triggers: list[str]
    max_duration_hours: int = 48
    auto_deactivate: bool = True
    description: str = ""
