"""Event type definitions for cross-division communication."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class BaseEvent(BaseModel):
    """Base class for all SFC events."""

    event_id: UUID = Field(default_factory=uuid4)
    event_type: str
    division: str
    run_id: str
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    priority: str = "medium"

    model_config = {"frozen": True}


class OpportunityDetected(BaseEvent):
    event_type: str = "opportunity_detected"


class TrendDetected(BaseEvent):
    event_type: str = "trend_detected"


class StoryCreated(BaseEvent):
    event_type: str = "story_created"


class CreativeCompleted(BaseEvent):
    event_type: str = "creative_completed"


class PublishingRequested(BaseEvent):
    event_type: str = "publishing_requested"


class PublishingCompleted(BaseEvent):
    event_type: str = "publishing_completed"


class PerformanceUpdated(BaseEvent):
    event_type: str = "performance_updated"


class RevenueOpportunityDetected(BaseEvent):
    event_type: str = "revenue_opportunity_detected"


class GovernanceApproved(BaseEvent):
    event_type: str = "governance_approved"


class GovernanceRejected(BaseEvent):
    event_type: str = "governance_rejected"


class IntelligenceBriefReady(BaseEvent):
    event_type: str = "intelligence_brief_ready"


class PlanningCycleStarted(BaseEvent):
    event_type: str = "planning_cycle_started"


class PlanningCycleCompleted(BaseEvent):
    event_type: str = "planning_cycle_completed"


class ContentDraftCreated(BaseEvent):
    event_type: str = "content_draft_created"


class AssetBriefCreated(BaseEvent):
    event_type: str = "asset_brief_created"


class EscalationRequired(BaseEvent):
    event_type: str = "escalation_required"


# Mapping from event_type string to class for deserialization
EVENT_TYPE_MAP: dict[str, type[BaseEvent]] = {
    "opportunity_detected": OpportunityDetected,
    "trend_detected": TrendDetected,
    "story_created": StoryCreated,
    "creative_completed": CreativeCompleted,
    "publishing_requested": PublishingRequested,
    "publishing_completed": PublishingCompleted,
    "performance_updated": PerformanceUpdated,
    "revenue_opportunity_detected": RevenueOpportunityDetected,
    "governance_approved": GovernanceApproved,
    "governance_rejected": GovernanceRejected,
    "intelligence_brief_ready": IntelligenceBriefReady,
    "planning_cycle_started": PlanningCycleStarted,
    "planning_cycle_completed": PlanningCycleCompleted,
    "content_draft_created": ContentDraftCreated,
    "asset_brief_created": AssetBriefCreated,
    "escalation_required": EscalationRequired,
}
