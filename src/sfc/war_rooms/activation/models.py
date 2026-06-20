"""Activation models for War Rooms."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel

from sfc.war_rooms.shared.types import WarRoomState, WarRoomType


class ActivationTrigger(str, Enum):
    MATCH_SCHEDULED = "match_scheduled"
    WORLD_CUP_MODE = "world_cup_mode"
    TRANSFER_WINDOW_OPEN = "transfer_window_open"
    CRISIS_DETECTED = "crisis_detected"
    EXECUTIVE_ACTIVATION = "executive_activation"
    MANUAL_OVERRIDE = "manual_override"


class ActivationRequest(BaseModel):
    war_room_type: WarRoomType
    trigger: ActivationTrigger
    requester: str = "system"
    metadata: dict[str, Any] = {}
    force: bool = False


class ActivationResult(BaseModel):
    success: bool
    war_room_id: str | None = None
    war_room_state: WarRoomState | None = None
    reasons: list[str] = []
    warnings: list[str] = []
    activated_at: datetime | None = None
