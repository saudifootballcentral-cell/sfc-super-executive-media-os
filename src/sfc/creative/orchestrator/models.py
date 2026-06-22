"""Creative Production Orchestrator models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ProductionPriority(str, Enum):
    URGENT = "urgent"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class ContentFormat(str, Enum):
    SHORT_VIDEO = "short_video"
    LONG_VIDEO = "long_video"
    IMAGE = "image"
    THUMBNAIL = "thumbnail"
    PODCAST = "podcast"
    THREAD = "thread"
    AUDIO = "audio"
    SHORTS_PACKAGE = "shorts_package"


class ProductionTrigger(str, Enum):
    NARRATIVE = "narrative"
    TREND = "trend"
    WAR_ROOM = "war_room"
    SCHEDULED = "scheduled"
    OPPORTUNITY = "opportunity"
    EXECUTIVE = "executive"


class AssetRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    content_format: ContentFormat
    title: str
    narrative: str = ""
    platform: str = ""
    priority: ProductionPriority = ProductionPriority.NORMAL
    context: dict[str, Any] = Field(default_factory=dict)
    persona_id: str = ""
    war_room_context: bool = False
    subject: str = ""

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class ProductionPlan(BaseModel):
    plan_id: str = Field(default_factory=lambda: str(uuid4()))
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    trigger: ProductionTrigger = ProductionTrigger.SCHEDULED
    asset_requests: list[AssetRequest] = Field(default_factory=list)
    priority: ProductionPriority = ProductionPriority.NORMAL
    narrative_context: str = ""
    trend_context: str = ""
    war_room_active: bool = False
    total_requests: int = 0
    estimated_production_time_minutes: float = 0.0
    persona_assignments: dict[str, str] = Field(default_factory=dict)
    ai_briefing: str = ""

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def to_summary(self) -> str:
        return (
            f"Production plan [{self.trigger.value}]: {self.total_requests} assets, "
            f"priority: {self.priority.value}, "
            f"est. {self.estimated_production_time_minutes:.0f} min."
        )
