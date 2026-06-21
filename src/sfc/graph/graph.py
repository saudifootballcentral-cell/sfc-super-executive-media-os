"""LangGraph StateGraph definition for SFC Super Executive Media OS.

Execution order
---------------
super_executive → war_room_router → planning → strategic_planning → intelligence
    → editorial → persona_layer → creative → governance → publishing
    → analytics → revenue_node → learning → memory_update → END

Package 6B extensions
---------------------
war_room_router: activates appropriate war room (crisis/match/transfer/world_cup)
                 based on task_type BEFORE planning begins.
persona_layer:   runs after editorial; uses PersonaRecommendationEngine to select
                 and execute top personas, enriching content_drafts metadata.
revenue_node:    runs after analytics; processes revenue_signals into a structured
                 revenue_summary inside analytics_report.

Parallel execution
------------------
Background tasks (analytics, revenue) run concurrently INSIDE planning_node
via asyncio.gather(). This keeps the LangGraph topology simple (no fan-in
edge conflicts) while fully respecting the constitutional principle:
"Sequential when required. Parallel when beneficial."

Governance gate
---------------
governance_node may route back to editorial for a revision cycle
before forwarding to publishing. Personas and war rooms CANNOT bypass
this gate — all publishing decisions still require governance approval.
"""

from __future__ import annotations

import logging
from typing import Any

from langgraph.graph import END, START, StateGraph

from sfc.graph.edges import route_after_executive, route_after_governance
from sfc.graph.nodes.analytics import analytics_node
from sfc.graph.nodes.creative import creative_node
from sfc.graph.nodes.editorial import editorial_node
from sfc.graph.nodes.governance import governance_node
from sfc.graph.nodes.intelligence import intelligence_node
from sfc.graph.nodes.learning import learning_node
from sfc.graph.nodes.memory_update import memory_update_node
from sfc.graph.nodes.persona_layer import persona_layer_node
from sfc.graph.nodes.planning import planning_node
from sfc.graph.nodes.publishing import publishing_node
from sfc.graph.nodes.revenue_node import revenue_node
from sfc.graph.nodes.strategic_planning import strategic_planning_node
from sfc.graph.nodes.super_executive import super_executive_node
from sfc.graph.nodes.war_room_router import war_room_router_node
from sfc.graph.state import SFCState

logger = logging.getLogger("sfc.graph")

SFCGraph = Any


def build_graph(checkpointer: Any = None) -> SFCGraph:
    """Build and compile the SFC Super Executive LangGraph pipeline.

    Args:
        checkpointer: Optional LangGraph checkpointer (MemorySaver, SqliteSaver, etc.)

    Returns:
        Compiled LangGraph graph ready to invoke.
    """
    builder = StateGraph(SFCState)

    # -----------------------------------------------------------------------
    # Register nodes
    # -----------------------------------------------------------------------
    builder.add_node("super_executive", super_executive_node)
    builder.add_node("war_room_router", war_room_router_node)   # Package 6B: war room activation
    builder.add_node("planning", planning_node)                  # includes async background tasks
    builder.add_node("strategic_planning", strategic_planning_node)
    builder.add_node("intelligence", intelligence_node)
    builder.add_node("editorial", editorial_node)
    builder.add_node("persona_layer", persona_layer_node)        # Package 6B: persona selection + execution
    builder.add_node("creative", creative_node)
    builder.add_node("governance", governance_node)
    builder.add_node("publishing", publishing_node)
    builder.add_node("analytics", analytics_node)
    builder.add_node("revenue_node", revenue_node)               # Package 6B: revenue signal processing
    builder.add_node("learning", learning_node)
    builder.add_node("memory_update", memory_update_node)

    # -----------------------------------------------------------------------
    # Wire edges
    # -----------------------------------------------------------------------
    builder.add_edge(START, "super_executive")

    # super_executive routes to war_room_router (or aborts to END)
    # route_after_executive returns "planning" → remapped to "war_room_router"
    builder.add_conditional_edges(
        "super_executive",
        route_after_executive,
        {"planning": "war_room_router", END: END},
    )

    builder.add_edge("war_room_router", "planning")
    builder.add_edge("planning", "strategic_planning")
    builder.add_edge("strategic_planning", "intelligence")
    builder.add_edge("intelligence", "editorial")
    builder.add_edge("editorial", "persona_layer")    # Package 6B: persona layer after editorial
    builder.add_edge("persona_layer", "creative")
    builder.add_edge("creative", "governance")

    builder.add_conditional_edges(
        "governance",
        route_after_governance,
        {"publishing": "publishing", "editorial": "editorial"},
    )

    builder.add_edge("publishing", "analytics")
    builder.add_edge("analytics", "revenue_node")     # Package 6B: revenue processing after analytics
    builder.add_edge("revenue_node", "learning")
    builder.add_edge("learning", "memory_update")
    builder.add_edge("memory_update", END)

    # -----------------------------------------------------------------------
    # Compile
    # -----------------------------------------------------------------------
    compile_kwargs: dict[str, Any] = {}
    if checkpointer is not None:
        compile_kwargs["checkpointer"] = checkpointer

    graph = builder.compile(**compile_kwargs)
    logger.info("[Graph] SFC pipeline compiled — 14 nodes (Package 6B: +war_room_router +persona_layer +revenue_node)")
    return graph


def get_graph_ascii() -> str:
    """Return an ASCII representation of the graph execution order."""
    return """
SFC SUPER EXECUTIVE MEDIA OS — LANGGRAPH PIPELINE (Package 6B)
===============================================================

  [START]
     │
     ▼
┌─────────────────┐
│ super_executive │  ← Claude executive decision
└─────────────────┘
     │ (conditional: abort → END)
     ▼
┌──────────────────┐
│ war_room_router  │  ← Package 6B: activates CrisisWarRoom / MatchDayWarRoom /
└──────────────────┘    TransferWindowWarRoom / WorldCupWarRoom / BreakingNewsCenter
     │
     ▼
┌──────────┐
│ planning │  ← Execution plan + parallel background work via asyncio.gather():
└──────────┘    • analytics_background  (historical benchmarks)
     │          • revenue_background    (sponsor signals → revenue_signals in state)
     ▼
┌──────────────────┐
│strategic_planning│  ← ICE scoring, annual/weekly plans
└──────────────────┘
     │
     ▼
┌─────────────┐
│ intelligence│  ← Source gathering, verification, confidence scoring
└─────────────┘
     │
     ▼
┌──────────┐
│ editorial│  ← Draft generation
└──────────┘
     │
     ▼
┌──────────────┐
│ persona_layer│  ← Package 6B: PersonaRecommendationEngine selects personas;
└──────────────┘    analyze() enriches content_drafts metadata (scores unchanged)
     │
     ▼
┌──────────┐
│ creative │  ← Asset briefs
└──────────┘
     │
     ▼
┌────────────┐
│ governance │  ← Constitutional enforcement (min 2 sources, confidence ≥ 85)
└────────────┘    Personas CANNOT bypass this gate.
     │ (conditional: rejected → editorial revision loop)
     ▼
┌───────────┐
│ publishing│  ← Platform distribution
└───────────┘
     │
     ▼
┌───────────┐
│ analytics │  ← Performance report
└───────────┘
     │
     ▼
┌─────────────┐
│ revenue_node│  ← Package 6B: processes revenue_signals → revenue_summary in analytics_report
└─────────────┘
     │
     ▼
┌──────────┐
│ learning │  ← Episodic memory extraction
└──────────┘
     │
     ▼
┌──────────────┐
│ memory_update│  ← Persists lessons to all memory stores
└──────────────┘
     │
   [END]
"""
