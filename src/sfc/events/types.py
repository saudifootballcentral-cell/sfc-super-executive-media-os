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


# ---------------------------------------------------------------------------
# Package 8: Autonomous Reporting & Scheduled Operations events
# ---------------------------------------------------------------------------

class ScheduledJobCreated(BaseEvent):
    event_type: str = "scheduled_job_created"


class ScheduledJobStarted(BaseEvent):
    event_type: str = "scheduled_job_started"


class ScheduledJobCompleted(BaseEvent):
    event_type: str = "scheduled_job_completed"


class ScheduledJobFailed(BaseEvent):
    event_type: str = "scheduled_job_failed"


class ReportGenerated(BaseEvent):
    event_type: str = "report_generated"


class ReportDelivered(BaseEvent):
    event_type: str = "report_delivered"


class AutonomousTriggerFired(BaseEvent):
    event_type: str = "autonomous_trigger_fired"


class BatchJobStarted(BaseEvent):
    event_type: str = "batch_job_started"


class BatchJobCompleted(BaseEvent):
    event_type: str = "batch_job_completed"


class ForecastGenerated(BaseEvent):
    event_type: str = "forecast_generated"


class BudgetAlertTriggered(BaseEvent):
    event_type: str = "budget_alert_triggered"


class CycleCompleted(BaseEvent):
    event_type: str = "cycle_completed"


# ---------------------------------------------------------------------------
# Package 8B: Social Intelligence & Trend Analysis Engine events
# ---------------------------------------------------------------------------

class TrendPeaked(BaseEvent):
    event_type: str = "trend_peaked"


class TrendDeclined(BaseEvent):
    event_type: str = "trend_declined"


class NarrativeDetected(BaseEvent):
    event_type: str = "narrative_detected"


class NarrativeShiftDetected(BaseEvent):
    event_type: str = "narrative_shift_detected"


class SentimentUpdated(BaseEvent):
    event_type: str = "sentiment_updated"


class SentimentCrisisDetected(BaseEvent):
    event_type: str = "sentiment_crisis_detected"


class InfluencerDetected(BaseEvent):
    event_type: str = "influencer_detected"


class ViralityForecastGenerated(BaseEvent):
    event_type: str = "virality_forecast_generated"


class SocialWarRoomActivated(BaseEvent):
    event_type: str = "social_war_room_activated"


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
    # Package 8
    "scheduled_job_created": ScheduledJobCreated,
    "scheduled_job_started": ScheduledJobStarted,
    "scheduled_job_completed": ScheduledJobCompleted,
    "scheduled_job_failed": ScheduledJobFailed,
    "report_generated": ReportGenerated,
    "report_delivered": ReportDelivered,
    "autonomous_trigger_fired": AutonomousTriggerFired,
    "batch_job_started": BatchJobStarted,
    "batch_job_completed": BatchJobCompleted,
    "forecast_generated": ForecastGenerated,
    "budget_alert_triggered": BudgetAlertTriggered,
    "cycle_completed": CycleCompleted,
    # Package 8B
    "trend_peaked": TrendPeaked,
    "trend_declined": TrendDeclined,
    "narrative_detected": NarrativeDetected,
    "narrative_shift_detected": NarrativeShiftDetected,
    "sentiment_updated": SentimentUpdated,
    "sentiment_crisis_detected": SentimentCrisisDetected,
    "influencer_detected": InfluencerDetected,
    "virality_forecast_generated": ViralityForecastGenerated,
    "social_war_room_activated": SocialWarRoomActivated,
}
