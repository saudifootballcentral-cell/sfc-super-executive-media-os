"""SFCState — the single typed state object that flows through the entire LangGraph pipeline."""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


class SFCState(TypedDict):
    """Shared state for the SFC Super Executive LangGraph pipeline.

    Execution order:
        super_executive → planning → [PARALLEL: intelligence + analytics_background + revenue_background]
        → editorial → creative → governance → publishing → analytics → learning → memory_update → END

    Parallel phase:
        intelligence, analytics_background, revenue_background all run simultaneously.
        analytics_background and revenue_background write to their own keys with no conflicts.
        The final analytics node acts as the join point (waits for publishing + both background nodes).
    """

    # -----------------------------------------------------------------------
    # INPUT — set before the graph runs
    # -----------------------------------------------------------------------
    run_id: str
    task_type: str          # TaskType enum value
    task_payload: dict[str, Any]

    # -----------------------------------------------------------------------
    # STAGE TRACKING
    # -----------------------------------------------------------------------
    pipeline_stage: str
    started_at: str
    completed_at: str | None

    # -----------------------------------------------------------------------
    # NODE: super_executive
    # Claude analyzes the task and makes the routing decision.
    # -----------------------------------------------------------------------
    executive_decision: dict[str, Any]

    # -----------------------------------------------------------------------
    # NODE: planning
    # Converts the executive decision into a detailed execution plan.
    # -----------------------------------------------------------------------
    execution_plan: dict[str, Any]

    # -----------------------------------------------------------------------
    # PARALLEL PHASE — all three nodes start simultaneously after planning
    # -----------------------------------------------------------------------

    # NODE: intelligence  (parallel #1, main — feeds editorial)
    intelligence_report: dict[str, Any]
    verified_sources: list[dict[str, Any]]

    # NODE: analytics_background  (parallel #2, independent)
    # Analyzes historical performance data — results consumed by analytics (final)
    analytics_background_data: dict[str, Any]

    # NODE: revenue_background  (parallel #3, independent)
    # Scans for monetization signals — results stored in state for publishing/planning
    revenue_signals: list[dict[str, Any]]

    # -----------------------------------------------------------------------
    # SEQUENTIAL MAIN CHAIN (starts after intelligence completes)
    # -----------------------------------------------------------------------

    # NODE: editorial
    content_drafts: list[dict[str, Any]]

    # NODE: creative
    creative_assets: list[dict[str, Any]]

    # NODE: governance
    governance_reviews: list[dict[str, Any]]
    approved_content: list[dict[str, Any]]
    rejected_content: list[dict[str, Any]]

    # NODE: publishing
    publish_queue: list[dict[str, Any]]
    publish_results: dict[str, Any]

    # -----------------------------------------------------------------------
    # NODE: analytics  (JOIN — waits for publishing + analytics_background + revenue_background)
    # -----------------------------------------------------------------------
    analytics_report: dict[str, Any]

    # -----------------------------------------------------------------------
    # NODE: learning
    # -----------------------------------------------------------------------
    lessons_learned: list[str]

    # -----------------------------------------------------------------------
    # NODE: memory_update
    # -----------------------------------------------------------------------
    memory_update_log: list[dict[str, Any]]

    # -----------------------------------------------------------------------
    # NODE: war_room_router  (between super_executive and planning)
    # -----------------------------------------------------------------------
    war_room_state: dict[str, Any]

    # -----------------------------------------------------------------------
    # NODE: persona_layer  (between editorial and creative)
    # -----------------------------------------------------------------------
    active_personas: list[str]
    persona_outputs: list[dict[str, Any]]

    # -----------------------------------------------------------------------
    # INFRASTRUCTURE
    # -----------------------------------------------------------------------
    infrastructure_ready: bool

    # -----------------------------------------------------------------------
    # AI METRICS (Package 7) — tracks AI usage per run
    # -----------------------------------------------------------------------
    ai_metrics: dict[str, Any]

    # -----------------------------------------------------------------------
    # PACKAGE 8: AUTONOMOUS REPORTING & SCHEDULED OPERATIONS
    # -----------------------------------------------------------------------

    # NODE: scheduler_node
    scheduler_state: dict[str, Any]

    # NODE: autonomous_trigger_node
    autonomous_triggers: list[dict[str, Any]]
    trigger_report: dict[str, Any]

    # NODE: executive_reporting_node
    executive_report: dict[str, Any]

    # NODE: operational_reporting_node
    operational_reports: list[dict[str, Any]]

    # NODE: historical_analytics_node
    historical_analytics: dict[str, Any]

    # NODE: cost_forecasting_node
    cost_forecast: dict[str, Any]

    # NODE: batch_processing_node
    batch_results: list[dict[str, Any]]

    # NODE: autonomous_execution_node
    autonomous_execution_plan: dict[str, Any]

    # NODE: report_delivery_node
    delivery_log: list[dict[str, Any]]
    delivery_stats: dict[str, Any]

    # -----------------------------------------------------------------------
    # PACKAGE 8B: SOCIAL INTELLIGENCE & TREND ANALYSIS ENGINE
    # -----------------------------------------------------------------------

    # NODE: social_intelligence_node (full scan orchestrator)
    social_intelligence_report: dict[str, Any]

    # NODE: trend_radar_node
    trend_radar_data: dict[str, Any]

    # NODE: narrative_intelligence_node
    narrative_intelligence_data: dict[str, Any]

    # NODE: fan_sentiment_node
    fan_sentiment_data: dict[str, Any]

    # NODE: influencer_intelligence_node
    influencer_data: dict[str, Any]

    # NODE: virality_prediction_node
    virality_forecast: dict[str, Any]

    # NODE: audience_intelligence_node
    audience_intelligence_data: dict[str, Any]

    # NODE: social_war_room_node
    social_war_room_state: dict[str, Any]

    # NODE: opportunity_detection_node
    opportunity_detections: list[dict[str, Any]]

    # Knowledge graph snapshot (updated by social_intelligence_node)
    social_knowledge_snapshot: dict[str, Any]

    # -----------------------------------------------------------------------
    # PACKAGE 8C: NARRATIVE INTELLIGENCE & AUDIENCE MODELING ENGINE
    # -----------------------------------------------------------------------

    # NODE: narrative_modeling_node
    narrative_models: dict[str, Any]

    # NODE: narrative_lifecycle_node
    narrative_lifecycle: dict[str, Any]

    # NODE: narrative_forecasting_node
    narrative_forecast: dict[str, Any]

    # NODE: narrative_risk_node
    narrative_risk: dict[str, Any]

    # NODE: audience_modeling_node
    audience_models: dict[str, Any]

    # NODE: audience_segmentation_node
    audience_segments: dict[str, Any]

    # NODE: audience_evolution_node
    audience_evolution: dict[str, Any]

    # NODE: influence_network_node
    influence_network: dict[str, Any]

    # NODE: reaction_simulator_node
    reaction_forecast: dict[str, Any]

    # NODE: narrative_strategy_node
    narrative_strategy: dict[str, Any]

    # NODE: narrative_command_center_node
    narrative_command_center: dict[str, Any]

    # -----------------------------------------------------------------------
    # Package 8E: Creative Production Layer
    # -----------------------------------------------------------------------
    production_plan: dict[str, Any]
    image_assets: list[dict[str, Any]]
    video_assets: list[dict[str, Any]]
    thumbnail_assets: list[dict[str, Any]]
    audio_assets: list[dict[str, Any]]
    shorts_packages: list[dict[str, Any]]
    podcast_episodes: list[dict[str, Any]]
    asset_registry: dict[str, Any]
    quality_reports: list[dict[str, Any]]
    content_packages: list[dict[str, Any]]

    # -----------------------------------------------------------------------
    # Package 9A: MVP Publishing & Intelligence Connectors
    # -----------------------------------------------------------------------
    youtube_results: dict[str, Any]
    x_results: dict[str, Any]
    buffer_queue_state: dict[str, Any]
    analytics_data: dict[str, Any]

    # -----------------------------------------------------------------------
    # ACCUMULATED WITH REDUCERS (safe for parallel writes)
    # -----------------------------------------------------------------------
    errors: Annotated[list[str], operator.add]
    warnings: Annotated[list[str], operator.add]


def make_initial_state(
    task_type: str,
    task_payload: dict[str, Any],
    run_id: str | None = None,
) -> SFCState:
    """Create a fully-initialised SFCState ready to enter the graph."""
    import uuid
    from datetime import datetime

    return SFCState(
        run_id=run_id or str(uuid.uuid4()),
        task_type=task_type,
        task_payload=task_payload,
        pipeline_stage="init",
        started_at=datetime.utcnow().isoformat(),
        completed_at=None,
        executive_decision={},
        execution_plan={},
        intelligence_report={},
        verified_sources=[],
        analytics_background_data={},
        revenue_signals=[],
        content_drafts=[],
        creative_assets=[],
        governance_reviews=[],
        approved_content=[],
        rejected_content=[],
        publish_queue=[],
        publish_results={},
        analytics_report={},
        lessons_learned=[],
        memory_update_log=[],
        war_room_state={},
        active_personas=[],
        persona_outputs=[],
        infrastructure_ready=False,
        ai_metrics={},
        # Package 8: Autonomous Reporting & Scheduled Operations
        scheduler_state={},
        autonomous_triggers=[],
        trigger_report={},
        executive_report={},
        operational_reports=[],
        historical_analytics={},
        cost_forecast={},
        batch_results=[],
        autonomous_execution_plan={},
        delivery_log=[],
        delivery_stats={},
        # Package 8B: Social Intelligence & Trend Analysis Engine
        social_intelligence_report={},
        trend_radar_data={},
        narrative_intelligence_data={},
        fan_sentiment_data={},
        influencer_data={},
        virality_forecast={},
        audience_intelligence_data={},
        social_war_room_state={},
        opportunity_detections=[],
        social_knowledge_snapshot={},
        # Package 8C: Narrative Intelligence & Audience Modeling Engine
        narrative_models={},
        narrative_lifecycle={},
        narrative_forecast={},
        narrative_risk={},
        audience_models={},
        audience_segments={},
        audience_evolution={},
        influence_network={},
        reaction_forecast={},
        narrative_strategy={},
        narrative_command_center={},
        # Package 8E: Creative Production Layer
        production_plan={},
        image_assets=[],
        video_assets=[],
        thumbnail_assets=[],
        audio_assets=[],
        shorts_packages=[],
        podcast_episodes=[],
        asset_registry={},
        quality_reports=[],
        content_packages=[],
        # Package 9A: Publishing & Intelligence Connectors
        youtube_results={},
        x_results={},
        buffer_queue_state={},
        analytics_data={},
        errors=[],
        warnings=[],
    )
