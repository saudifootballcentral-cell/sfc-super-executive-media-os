"""Social & Narrative Intelligence Graph — Package 8D LangGraph pipeline.

This graph integrates all Package 8B and Package 8C nodes into a unified
intelligence scanning pipeline. It is designed to run on a schedule
(hourly or at match-day intervals) independently of the main content
production pipeline.

Execution order
---------------
social_intelligence_node (orchestrator)
  → trend_radar_node              (8B: top trends and velocity)
  → fan_sentiment_node            (8B: real-time fan sentiment)
  → narrative_intelligence_node   (8B: social narrative detection)
  → influencer_intelligence_node  (8B: influencer mapping)
  → virality_prediction_node      (8B: virality forecasting)
  → audience_intelligence_node    (8B: audience intelligence)
  → opportunity_detection_node    (8B: content opportunity detection)
  → social_war_room_node          (8B: social crisis triage)
  → narrative_modeling_node       (8C: deep narrative profiling)
  → narrative_lifecycle_node      (8C: lifecycle stage analysis)
  → narrative_forecasting_node    (8C: multi-horizon forecasting)
  → narrative_risk_node           (8C: risk assessment)
  → narrative_strategy_node       (8C: strategy recommendations)
  → audience_modeling_node        (8C: audience digital twins)
  → audience_segmentation_node    (8C: audience clusters)
  → audience_evolution_node       (8C: growth/retention forecasting)
  → influence_network_node        (8C: influence network mapping)
  → reaction_simulator_node       (8C: scenario simulation)
  → narrative_command_center_node (8C: full intelligence dashboard)
  → memory_update                 (persist all intelligence to memory)
  → END

Governance requirement
----------------------
This graph is READ-ONLY intelligence. No content is published from this
pipeline. Any war room activations or escalations flagged here must route
through the MAIN pipeline (graph.py) governance gate before any action.
"""

from __future__ import annotations

import logging
from typing import Any

from langgraph.graph import END, START, StateGraph

# Package 8B nodes
from sfc.graph.nodes.social_intelligence_node import social_intelligence_node
from sfc.graph.nodes.trend_radar_node import trend_radar_node
from sfc.graph.nodes.fan_sentiment_node import fan_sentiment_node
from sfc.graph.nodes.narrative_intelligence_node import narrative_intelligence_node
from sfc.graph.nodes.influencer_intelligence_node import influencer_intelligence_node
from sfc.graph.nodes.virality_prediction_node import virality_prediction_node
from sfc.graph.nodes.audience_intelligence_node import audience_intelligence_node
from sfc.graph.nodes.opportunity_detection_node import opportunity_detection_node
from sfc.graph.nodes.social_war_room_node import social_war_room_node

# Package 8C nodes
from sfc.graph.nodes.narrative_modeling_node import narrative_modeling_node
from sfc.graph.nodes.narrative_lifecycle_node import narrative_lifecycle_node
from sfc.graph.nodes.narrative_forecasting_node import narrative_forecasting_node
from sfc.graph.nodes.narrative_risk_node import narrative_risk_node
from sfc.graph.nodes.narrative_strategy_node import narrative_strategy_node
from sfc.graph.nodes.audience_modeling_node import audience_modeling_node
from sfc.graph.nodes.audience_segmentation_node import audience_segmentation_node
from sfc.graph.nodes.audience_evolution_node import audience_evolution_node
from sfc.graph.nodes.influence_network_node import influence_network_node
from sfc.graph.nodes.reaction_simulator_node import reaction_simulator_node
from sfc.graph.nodes.narrative_command_center_node import narrative_command_center_node

# Shared
from sfc.graph.nodes.memory_update import memory_update_node
from sfc.graph.state import SFCState

logger = logging.getLogger("sfc.graph.social_intelligence")

SocialIntelligenceGraph = Any


def build_social_intelligence_graph(checkpointer: Any = None) -> SocialIntelligenceGraph:
    """Build and compile the Package 8D social and narrative intelligence pipeline.

    Args:
        checkpointer: Optional LangGraph checkpointer for persistence.

    Returns:
        Compiled LangGraph graph ready to invoke.
    """
    builder = StateGraph(SFCState)

    # ------------------------------------------------------------------
    # Register Package 8B nodes
    # ------------------------------------------------------------------
    builder.add_node("social_intelligence", social_intelligence_node)
    builder.add_node("trend_radar", trend_radar_node)
    builder.add_node("fan_sentiment", fan_sentiment_node)
    builder.add_node("narrative_intelligence", narrative_intelligence_node)
    builder.add_node("influencer_intelligence", influencer_intelligence_node)
    builder.add_node("virality_prediction", virality_prediction_node)
    builder.add_node("audience_intelligence", audience_intelligence_node)
    builder.add_node("opportunity_detection", opportunity_detection_node)
    builder.add_node("social_war_room", social_war_room_node)

    # ------------------------------------------------------------------
    # Register Package 8C nodes
    # Node aliases ending in _step avoid clashing with identically-named
    # SFCState keys (LangGraph enforces uniqueness across nodes and keys).
    # ------------------------------------------------------------------
    builder.add_node("narrative_modeling", narrative_modeling_node)
    builder.add_node("narrative_lifecycle_step", narrative_lifecycle_node)
    builder.add_node("narrative_forecasting", narrative_forecasting_node)
    builder.add_node("narrative_risk_step", narrative_risk_node)
    builder.add_node("narrative_strategy_step", narrative_strategy_node)
    builder.add_node("audience_modeling", audience_modeling_node)
    builder.add_node("audience_segmentation", audience_segmentation_node)
    builder.add_node("audience_evolution_step", audience_evolution_node)
    builder.add_node("influence_network_step", influence_network_node)
    builder.add_node("reaction_simulator", reaction_simulator_node)
    builder.add_node("narrative_command_center_step", narrative_command_center_node)

    # ------------------------------------------------------------------
    # Shared
    # ------------------------------------------------------------------
    builder.add_node("memory_update", memory_update_node)

    # ------------------------------------------------------------------
    # Wire Package 8B chain
    # ------------------------------------------------------------------
    builder.add_edge(START, "social_intelligence")
    builder.add_edge("social_intelligence", "trend_radar")
    builder.add_edge("trend_radar", "fan_sentiment")
    builder.add_edge("fan_sentiment", "narrative_intelligence")
    builder.add_edge("narrative_intelligence", "influencer_intelligence")
    builder.add_edge("influencer_intelligence", "virality_prediction")
    builder.add_edge("virality_prediction", "audience_intelligence")
    builder.add_edge("audience_intelligence", "opportunity_detection")
    builder.add_edge("opportunity_detection", "social_war_room")

    # ------------------------------------------------------------------
    # Transition from 8B to 8C: social war room feeds narrative modeling
    # ------------------------------------------------------------------
    builder.add_edge("social_war_room", "narrative_modeling")

    # ------------------------------------------------------------------
    # Wire Package 8C chain
    # ------------------------------------------------------------------
    builder.add_edge("narrative_modeling", "narrative_lifecycle_step")
    builder.add_edge("narrative_lifecycle_step", "narrative_forecasting")
    builder.add_edge("narrative_forecasting", "narrative_risk_step")
    builder.add_edge("narrative_risk_step", "narrative_strategy_step")
    builder.add_edge("narrative_strategy_step", "audience_modeling")
    builder.add_edge("audience_modeling", "audience_segmentation")
    builder.add_edge("audience_segmentation", "audience_evolution_step")
    builder.add_edge("audience_evolution_step", "influence_network_step")
    builder.add_edge("influence_network_step", "reaction_simulator")
    builder.add_edge("reaction_simulator", "narrative_command_center_step")

    # ------------------------------------------------------------------
    # Persist and complete
    # ------------------------------------------------------------------
    builder.add_edge("narrative_command_center_step", "memory_update")
    builder.add_edge("memory_update", END)

    # ------------------------------------------------------------------
    # Compile
    # ------------------------------------------------------------------
    compile_kwargs: dict[str, Any] = {}
    if checkpointer is not None:
        compile_kwargs["checkpointer"] = checkpointer

    graph = builder.compile(**compile_kwargs)
    logger.info(
        "[SocialIntelligenceGraph] Package 8D compiled — "
        "9 Package 8B nodes + 11 Package 8C nodes + memory_update = 21 nodes"
    )
    return graph


def get_social_intelligence_graph_ascii() -> str:
    """Return ASCII diagram of the social and narrative intelligence pipeline."""
    return """
SFC SOCIAL & NARRATIVE INTELLIGENCE PIPELINE (Package 8D)
==========================================================

  [START]
     │
     ▼
┌──────────────────────┐
│  social_intelligence │  ← 8B: Full social scan orchestrator
└──────────────────────┘
     │
     ▼
┌─────────────┐
│ trend_radar │  ← 8B: Top trends by velocity and reach
└─────────────┘
     │
     ▼
┌───────────────┐
│ fan_sentiment │  ← 8B: Real-time fan mood across platforms
└───────────────┘
     │
     ▼
┌───────────────────────────┐
│ narrative_intelligence    │  ← 8B: Social narrative detection (NarrativeReport)
└───────────────────────────┘
     │
     ▼
┌────────────────────────────┐
│ influencer_intelligence    │  ← 8B: Influencer mapping and classification
└────────────────────────────┘
     │
     ▼
┌──────────────────────┐
│ virality_prediction  │  ← 8B: Content virality forecast
└──────────────────────┘
     │
     ▼
┌─────────────────────────┐
│ audience_intelligence   │  ← 8B: Audience segment intelligence
└─────────────────────────┘
     │
     ▼
┌──────────────────────┐
│ opportunity_detection│  ← 8B: Content opportunity scoring
└──────────────────────┘
     │
     ▼
┌──────────────────┐
│ social_war_room  │  ← 8B: Social crisis triage and activation
└──────────────────┘
     │
     ▼  [8B → 8C handoff]
┌────────────────────┐
│ narrative_modeling │  ← 8C: Deep narrative profiling (NarrativeMap)
└────────────────────┘
     │
     ▼
┌─────────────────────┐
│ narrative_lifecycle │  ← 8C: Stage analysis (SEED→DEAD)
└─────────────────────┘
     │
     ▼
┌───────────────────────┐
│ narrative_forecasting │  ← 8C: 24h/72h/7d/30d/90d forecasts
└───────────────────────┘
     │
     ▼
┌─────────────────┐
│ narrative_risk  │  ← 8C: 7-type risk scoring + war room flags
└─────────────────┘
     │
     ▼
┌────────────────────┐
│ narrative_strategy │  ← 8C: Strategy actions (AMPLIFY/COUNTER/etc)
└────────────────────┘
     │
     ▼
┌──────────────────┐
│ audience_modeling│  ← 8C: Digital twins for 7 audience types
└──────────────────┘
     │
     ▼
┌──────────────────────────┐
│ audience_segmentation    │  ← 8C: 8-cluster audience segments
└──────────────────────────┘
     │
     ▼
┌───────────────────┐
│ audience_evolution│  ← 8C: Growth/retention + platform migration
└───────────────────┘
     │
     ▼
┌───────────────────┐
│ influence_network │  ← 8C: 12-node Saudi football media map
└───────────────────┘
     │
     ▼
┌────────────────────┐
│ reaction_simulator │  ← 8C: Scenario-based reaction forecasting
└────────────────────┘
     │
     ▼
┌─────────────────────────────┐
│ narrative_command_center    │  ← 8C: Full intelligence dashboard
└─────────────────────────────┘
     │
     ▼
┌───────────────┐
│ memory_update │  ← Persists all intelligence to memory layers
└───────────────┘
     │
   [END]

GOVERNANCE: This pipeline is READ-ONLY intelligence.
No content is published from this graph.
War room escalations from narrative_risk or social_war_room
MUST route through the main pipeline governance gate.
"""
