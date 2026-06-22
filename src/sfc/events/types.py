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


# ---------------------------------------------------------------------------
# Package 8C: Narrative Intelligence & Audience Modeling Engine events
# ---------------------------------------------------------------------------

class NarrativeForecastGenerated(BaseEvent):
    event_type: str = "narrative_forecast_generated"


class NarrativeRiskDetected(BaseEvent):
    event_type: str = "narrative_risk_detected"


class AudienceSegmentUpdated(BaseEvent):
    event_type: str = "audience_segment_updated"


class AudienceBehaviorChanged(BaseEvent):
    event_type: str = "audience_behavior_changed"


class InfluenceNetworkUpdated(BaseEvent):
    event_type: str = "influence_network_updated"


class ReactionSimulationCompleted(BaseEvent):
    event_type: str = "reaction_simulation_completed"


class NarrativeStrategyRecommended(BaseEvent):
    event_type: str = "narrative_strategy_recommended"


class NarrativeEscalationTriggered(BaseEvent):
    event_type: str = "narrative_escalation_triggered"


# Package 8E: Creative Production Layer events
class ProductionPlanCreated(BaseEvent):
    event_type: str = "production_plan_created"


class ImageAssetsGenerated(BaseEvent):
    event_type: str = "image_assets_generated"


class VideoAssetsGenerated(BaseEvent):
    event_type: str = "video_assets_generated"


class ShortsPackageGenerated(BaseEvent):
    event_type: str = "shorts_package_generated"


class PodcastEpisodeGenerated(BaseEvent):
    event_type: str = "podcast_episode_generated"


class QualityReviewCompleted(BaseEvent):
    event_type: str = "quality_review_completed"


class ContentPackageReady(BaseEvent):
    event_type: str = "content_package_ready"


class CreativeProductionCompleted(BaseEvent):
    event_type: str = "creative_production_completed"


# Package 9A: Publishing & Intelligence Connector events
class VideoPublished(BaseEvent):
    event_type: str = "video_published"


class AnalyticsUpdated(BaseEvent):
    event_type: str = "analytics_updated"


class ChannelGrowthUpdated(BaseEvent):
    event_type: str = "channel_growth_updated"


class XPostPublished(BaseEvent):
    event_type: str = "x_post_published"


class XThreadPublished(BaseEvent):
    event_type: str = "x_thread_published"


class XConversationDetected(BaseEvent):
    event_type: str = "x_conversation_detected"


class BufferPostCreated(BaseEvent):
    event_type: str = "buffer_post_created"


class BufferPostPublished(BaseEvent):
    event_type: str = "buffer_post_published"


class BufferPostFailed(BaseEvent):
    event_type: str = "buffer_post_failed"


# ---------------------------------------------------------------------------
# Package 10D: Master Orchestrator events
# ---------------------------------------------------------------------------

class OrchestrationStarted(BaseEvent):
    event_type: str = "orchestration_started"


class OrchestrationCompleted(BaseEvent):
    event_type: str = "orchestration_completed"


class OrchestrationFailed(BaseEvent):
    event_type: str = "orchestration_failed"


class OrchestrationAborted(BaseEvent):
    event_type: str = "orchestration_aborted"


class StageStarted(BaseEvent):
    event_type: str = "stage_started"


class StageCompleted(BaseEvent):
    event_type: str = "stage_completed"


class StageFailed(BaseEvent):
    event_type: str = "stage_failed"


class StageSkipped(BaseEvent):
    event_type: str = "stage_skipped"


class OperatorApprovalRequested(BaseEvent):
    event_type: str = "operator_approval_requested"


class OperatorApprovalGranted(BaseEvent):
    event_type: str = "operator_approval_granted"


class OperatorApprovalDenied(BaseEvent):
    event_type: str = "operator_approval_denied"


class DataIngestionCompleted(BaseEvent):
    event_type: str = "data_ingestion_completed"


class SocialIntelligenceRunCompleted(BaseEvent):
    event_type: str = "social_intelligence_run_completed"


class NarrativeIntelligenceRunCompleted(BaseEvent):
    event_type: str = "narrative_intelligence_run_completed"


class CreativeProductionRunCompleted(BaseEvent):
    event_type: str = "creative_production_run_completed"


class ConnectorRunCompleted(BaseEvent):
    event_type: str = "connector_run_completed"


class WorkflowCheckpointSaved(BaseEvent):
    event_type: str = "workflow_checkpoint_saved"


class RecoveryAttempted(BaseEvent):
    event_type: str = "recovery_attempted"


class DryRunCompleted(BaseEvent):
    event_type: str = "dry_run_completed"


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
    # Package 8C
    "narrative_forecast_generated": NarrativeForecastGenerated,
    "narrative_risk_detected": NarrativeRiskDetected,
    "audience_segment_updated": AudienceSegmentUpdated,
    "audience_behavior_changed": AudienceBehaviorChanged,
    "influence_network_updated": InfluenceNetworkUpdated,
    "reaction_simulation_completed": ReactionSimulationCompleted,
    "narrative_strategy_recommended": NarrativeStrategyRecommended,
    "narrative_escalation_triggered": NarrativeEscalationTriggered,
    # Package 8E
    "production_plan_created": ProductionPlanCreated,
    "image_assets_generated": ImageAssetsGenerated,
    "video_assets_generated": VideoAssetsGenerated,
    "shorts_package_generated": ShortsPackageGenerated,
    "podcast_episode_generated": PodcastEpisodeGenerated,
    "quality_review_completed": QualityReviewCompleted,
    "content_package_ready": ContentPackageReady,
    "creative_production_completed": CreativeProductionCompleted,
    # Package 9A
    "video_published": VideoPublished,
    "analytics_updated": AnalyticsUpdated,
    "channel_growth_updated": ChannelGrowthUpdated,
    "x_post_published": XPostPublished,
    "x_thread_published": XThreadPublished,
    "x_conversation_detected": XConversationDetected,
    "buffer_post_created": BufferPostCreated,
    "buffer_post_published": BufferPostPublished,
    "buffer_post_failed": BufferPostFailed,
    # Package 10D
    "orchestration_started": OrchestrationStarted,
    "orchestration_completed": OrchestrationCompleted,
    "orchestration_failed": OrchestrationFailed,
    "orchestration_aborted": OrchestrationAborted,
    "stage_started": StageStarted,
    "stage_completed": StageCompleted,
    "stage_failed": StageFailed,
    "stage_skipped": StageSkipped,
    "operator_approval_requested": OperatorApprovalRequested,
    "operator_approval_granted": OperatorApprovalGranted,
    "operator_approval_denied": OperatorApprovalDenied,
    "data_ingestion_completed": DataIngestionCompleted,
    "social_intelligence_run_completed": SocialIntelligenceRunCompleted,
    "narrative_intelligence_run_completed": NarrativeIntelligenceRunCompleted,
    "creative_production_run_completed": CreativeProductionRunCompleted,
    "connector_run_completed": ConnectorRunCompleted,
    "workflow_checkpoint_saved": WorkflowCheckpointSaved,
    "recovery_attempted": RecoveryAttempted,
    "dry_run_completed": DryRunCompleted,
}
