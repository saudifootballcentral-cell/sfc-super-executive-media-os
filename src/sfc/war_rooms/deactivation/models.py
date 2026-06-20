"""Deactivation models for War Rooms."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from sfc.war_rooms.shared.types import WarRoomMetrics


class ClosureReport(BaseModel):
    war_room_id: str
    war_room_type: str
    activated_at: datetime | None
    deactivated_at: datetime
    duration_minutes: float
    metrics: WarRoomMetrics
    lessons_learned: list[str]
    decisions_made: list[str]
    events_processed: int
    final_status: str


class DeactivationResult(BaseModel):
    success: bool
    war_room_id: str
    closure_report: ClosureReport | None = None
    errors: list[str] = []
