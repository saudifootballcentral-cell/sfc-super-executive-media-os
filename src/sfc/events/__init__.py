"""SFC Events — cross-division async event infrastructure."""

from __future__ import annotations

from sfc.events.bus import EventBus, get_event_bus
from sfc.events.types import (
    AssetBriefCreated,
    BaseEvent,
    ContentDraftCreated,
    CreativeCompleted,
    EscalationRequired,
    GovernanceApproved,
    GovernanceRejected,
    IntelligenceBriefReady,
    OpportunityDetected,
    PerformanceUpdated,
    PlanningCycleCompleted,
    PlanningCycleStarted,
    PublishingCompleted,
    PublishingRequested,
    RevenueOpportunityDetected,
    StoryCreated,
    TrendDetected,
)

__all__ = [
    "BaseEvent",
    "EventBus",
    "get_event_bus",
    "OpportunityDetected",
    "TrendDetected",
    "StoryCreated",
    "CreativeCompleted",
    "PublishingRequested",
    "PublishingCompleted",
    "PerformanceUpdated",
    "RevenueOpportunityDetected",
    "GovernanceApproved",
    "GovernanceRejected",
    "IntelligenceBriefReady",
    "PlanningCycleStarted",
    "PlanningCycleCompleted",
    "ContentDraftCreated",
    "AssetBriefCreated",
    "EscalationRequired",
]
