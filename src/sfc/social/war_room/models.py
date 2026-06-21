"""Social War Room models — triggers, states, and reports."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class SocialWarRoomTrigger(str, Enum):
    NARRATIVE_SPIKE = "narrative_spike"
    SENTIMENT_CRISIS = "sentiment_crisis"
    TRANSFER_EXPLOSION = "transfer_explosion"
    BREAKING_STORY = "breaking_story"
    NATIONAL_TEAM_CRISIS = "national_team_crisis"
    REFEREE_CONTROVERSY = "referee_controversy"
    MEDIA_ATTACK = "media_attack"


class WarRoomPriority(str, Enum):
    P1 = "P1"   # Critical — immediate response required
    P2 = "P2"   # High — response within 1 hour
    P3 = "P3"   # Medium — response within 4 hours


class WarRoomStatus(str, Enum):
    ACTIVE = "active"
    MONITORING = "monitoring"
    RESPONDING = "responding"
    RESOLVED = "resolved"


class SocialWarRoomState(BaseModel):
    war_room_id: str = Field(default_factory=lambda: str(uuid4()))
    trigger: SocialWarRoomTrigger
    priority: WarRoomPriority = WarRoomPriority.P1
    status: WarRoomStatus = WarRoomStatus.ACTIVE
    context: dict[str, Any] = Field(default_factory=dict)
    activated_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: datetime | None = None
    assigned_personas: list[str] = Field(default_factory=list)

    model_config = {"frozen": False}


class SocialWarRoomReport(BaseModel):
    report_id: str = Field(default_factory=lambda: str(uuid4()))
    war_room_id: str = ""
    trigger: SocialWarRoomTrigger = SocialWarRoomTrigger.BREAKING_STORY
    priority: WarRoomPriority = WarRoomPriority.P1
    status: WarRoomStatus = WarRoomStatus.ACTIVE
    context_summary: str = ""
    recommended_responses: list[str] = Field(default_factory=list)
    narrative_strategies: list[str] = Field(default_factory=list)
    executive_alerts: list[str] = Field(default_factory=list)
    persona_assignments: dict[str, str] = Field(default_factory=dict)  # persona → role
    activated_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: datetime | None = None

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def to_summary(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "trigger": self.trigger.value,
            "priority": self.priority.value,
            "status": self.status.value,
            "activated_at": self.activated_at.isoformat(),
        }
