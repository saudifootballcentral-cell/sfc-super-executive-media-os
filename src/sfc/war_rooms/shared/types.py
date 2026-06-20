"""Shared types for the War Rooms subsystem."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class WarRoomStatus(str, Enum):
    INACTIVE = "inactive"
    ACTIVATING = "activating"
    ACTIVE = "active"
    ESCALATED = "escalated"
    DEACTIVATING = "deactivating"
    CLOSED = "closed"


class WarRoomPriority(str, Enum):
    P1_CRITICAL = "p1_critical"
    P2_HIGH = "p2_high"
    P3_MEDIUM = "p3_medium"
    P4_LOW = "p4_low"


class WarRoomType(str, Enum):
    MATCH_DAY = "match_day"
    WORLD_CUP = "world_cup"
    TRANSFER_WINDOW = "transfer_window"
    CRISIS = "crisis"


class WarRoomState(BaseModel):
    war_room_id: str
    war_room_type: WarRoomType
    status: WarRoomStatus = WarRoomStatus.INACTIVE
    priority: WarRoomPriority
    owner: str = "super_executive"
    activation_time: datetime | None = None
    deactivation_time: datetime | None = None
    assigned_divisions: list[str] = []
    active_events: list[str] = []
    health_score: float = 100.0
    resource_profile: dict[str, Any] = {}
    escalations: list[dict[str, Any]] = []
    run_ids: list[str] = []
    metadata: dict[str, Any] = {}


class WarRoomMetrics(BaseModel):
    war_room_id: str
    content_pieces_produced: int = 0
    governance_pass_rate: float = 0.0
    avg_confidence_score: float = 0.0
    total_reach_estimate: int = 0
    escalations: int = 0
    errors: int = 0
    duration_minutes: float = 0.0
    revenue_signals: int = 0


class WarRoomHealth(BaseModel):
    war_room_id: str
    status: str
    health_score: float
    assigned_divisions_healthy: bool = True
    resource_utilization: float = 0.0
    last_event_at: datetime | None = None
    warnings: list[str] = []


class WarRoomAllocation(BaseModel):
    war_room_id: str
    divisions: list[str]
    capabilities: list[str]
    memory_namespace: str
    priority_slots: int
    allocated_at: datetime = Field(default_factory=datetime.utcnow)
