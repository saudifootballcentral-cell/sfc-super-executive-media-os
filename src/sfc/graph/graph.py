"""LangGraph StateGraph definition for SFC Super Executive Media OS.

Execution order
---------------
super_executive → planning → intelligence → editorial → creative
    → governance → publishing → analytics → learning → memory_update → END

Parallel execution
------------------
Background tasks (analytics, revenue) run concurrently INSIDE planning_node
via asyncio.gather(). This keeps the LangGraph topology simple (no fan-in
edge conflicts) while fully respecting the constitutional principle:
"Sequential when required. Parallel when beneficial."

Governance gate
---------------
governance_node may route back to editorial for a revision cycle
before forwarding to publishing.
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
from sfc.graph.nodes.planning import planning_node
from sfc.graph.nodes.publishing import publishing_node
from sfc.graph.nodes.super_executive import super_executive_node
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
    builder.add_node("planning", planning_node)          # includes async background tasks
    builder.add_node("intelligence", intelligence_node)
    builder.add_node("editorial", editorial_node)
    builder.add_node("creative", creative_node)
    builder.add_node("governance", governance_node)
    builder.add_node("publishing", publishing_node)
    builder.add_node("analytics", analytics_node)
    builder.add_node("learning", learning_node)
    builder.add_node("memory_update", memory_update_node)

    # -----------------------------------------------------------------------
    # Wire edges
    # -----------------------------------------------------------------------
    builder.add_edge(START, "super_executive")

    builder.add_conditional_edges(
        "super_executive",
        route_after_executive,
        {"planning": "planning", END: END},
    )

    builder.add_edge("planning", "intelligence")
    builder.add_edge("intelligence", "editorial")
    builder.add_edge("editorial", "creative")
    builder.add_edge("creative", "governance")

    builder.add_conditional_edges(
        "governance",
        route_after_governance,
        {"publishing": "publishing", "editorial": "editorial"},
    )

    builder.add_edge("publishing", "analytics")
    builder.add_edge("analytics", "learning")
    builder.add_edge("learning", "memory_update")
    builder.add_edge("memory_update", END)

    # -----------------------------------------------------------------------
    # Compile
    # -----------------------------------------------------------------------
    compile_kwargs: dict[str, Any] = {}
    if checkpointer is not None:
        compile_kwargs["checkpointer"] = checkpointer

    graph = builder.compile(**compile_kwargs)
    logger.info("[Graph] SFC pipeline compiled — 10 nodes")
    return graph


def get_graph_ascii() -> str:
    """Return an ASCII representation of the graph execution order."""
    return """
SFC SUPER EXECUTIVE MEDIA OS — LANGGRAPH PIPELINE
==================================================

  [START]
     │
     ▼
┌─────────────────┐
│ super_executive │  ← Claude (claude-opus-4-8) executive decision
└─────────────────┘
     │ (conditional: abort → END)
     ▼
┌──────────┐
│ planning │  ← Execution plan + parallel background work via asyncio.gather():
└──────────┘    • analytics_background  (historical benchmarks)
     │          • revenue_background    (sponsor signals)
     ▼
┌─────────────┐
│ intelligence│  ← Source gathering, verification, confidence scoring
└─────────────┘
     │
     ▼
┌──────────┐
│ editorial│  ← Draft generation (Package 2: EditorialDivision)
└──────────┘
     │
     ▼
┌──────────┐
│ creative │  ← Asset briefs (Package 2: CreativeDivision)
└──────────┘
     │
     ▼
┌────────────┐
│ governance │  ← Constitutional enforcement (min 2 sources, confidence ≥ 85)
└────────────┘
     │ (conditional: rejected → editorial revision loop)
     ▼
┌───────────┐
│ publishing│  ← Platform distribution (Package 2: PublishingDivision)
└───────────┘
     │
     ▼
┌───────────┐
│ analytics │  ← Combines publish results + background data + revenue signals
└───────────┘
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
