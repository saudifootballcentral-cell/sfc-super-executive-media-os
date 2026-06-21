"""Autonomous Reporting Graph — Package 8 LangGraph pipeline.

This is a separate graph for autonomous reporting cycles (daily briefs,
weekly reports, trend analysis, cost forecasting, etc.).

It complements the main pipeline graph (graph.py) which handles individual
content production tasks. This graph handles recurring autonomous operations.

Execution order
---------------
scheduler_node → autonomous_trigger_node → autonomous_execution_node
    → [parallel] executive_reporting_node + operational_reporting_node
                 + historical_analytics_node + cost_forecasting_node
    → batch_processing_node → report_delivery_node → memory_update → END

Governance requirement
----------------------
Autonomous publishing via this graph MUST still call the main pipeline graph,
which routes through governance_node. No content bypasses the governance gate.
"""

from __future__ import annotations

import logging
from typing import Any

from langgraph.graph import END, START, StateGraph

from sfc.graph.nodes.scheduler_node import scheduler_node
from sfc.graph.nodes.autonomous_trigger_node import autonomous_trigger_node
from sfc.graph.nodes.autonomous_execution_node import autonomous_execution_node
from sfc.graph.nodes.executive_reporting_node import executive_reporting_node
from sfc.graph.nodes.operational_reporting_node import operational_reporting_node
from sfc.graph.nodes.historical_analytics_node import historical_analytics_node
from sfc.graph.nodes.cost_forecasting_node import cost_forecasting_node
from sfc.graph.nodes.batch_processing_node import batch_processing_node
from sfc.graph.nodes.report_delivery_node import report_delivery_node
from sfc.graph.nodes.memory_update import memory_update_node
from sfc.graph.state import SFCState

logger = logging.getLogger("sfc.graph.autonomous")

AutonomousGraph = Any


def build_autonomous_graph(checkpointer: Any = None) -> AutonomousGraph:
    """Build and compile the Package 8 autonomous reporting pipeline.

    Args:
        checkpointer: Optional LangGraph checkpointer for persistence.

    Returns:
        Compiled LangGraph graph ready to invoke.
    """
    builder = StateGraph(SFCState)

    # ------------------------------------------------------------------
    # Register Package 8 nodes
    # ------------------------------------------------------------------
    builder.add_node("scheduler_node", scheduler_node)
    builder.add_node("autonomous_trigger_node", autonomous_trigger_node)
    builder.add_node("autonomous_execution_node", autonomous_execution_node)
    builder.add_node("executive_reporting_node", executive_reporting_node)
    builder.add_node("operational_reporting_node", operational_reporting_node)
    builder.add_node("historical_analytics_node", historical_analytics_node)
    builder.add_node("cost_forecasting_node", cost_forecasting_node)
    builder.add_node("batch_processing_node", batch_processing_node)
    builder.add_node("report_delivery_node", report_delivery_node)
    builder.add_node("memory_update", memory_update_node)

    # ------------------------------------------------------------------
    # Wire edges
    # ------------------------------------------------------------------
    builder.add_edge(START, "scheduler_node")
    builder.add_edge("scheduler_node", "autonomous_trigger_node")
    builder.add_edge("autonomous_trigger_node", "autonomous_execution_node")

    # After execution coordination, run all analytics/reporting nodes concurrently
    # (LangGraph fan-out via multiple edges from one node)
    builder.add_edge("autonomous_execution_node", "executive_reporting_node")
    builder.add_edge("autonomous_execution_node", "operational_reporting_node")
    builder.add_edge("autonomous_execution_node", "historical_analytics_node")
    builder.add_edge("autonomous_execution_node", "cost_forecasting_node")

    # Fan-in to batch processing (all 4 parallel nodes must complete first)
    builder.add_edge("executive_reporting_node", "batch_processing_node")
    builder.add_edge("operational_reporting_node", "batch_processing_node")
    builder.add_edge("historical_analytics_node", "batch_processing_node")
    builder.add_edge("cost_forecasting_node", "batch_processing_node")

    builder.add_edge("batch_processing_node", "report_delivery_node")
    builder.add_edge("report_delivery_node", "memory_update")
    builder.add_edge("memory_update", END)

    # ------------------------------------------------------------------
    # Compile
    # ------------------------------------------------------------------
    compile_kwargs: dict[str, Any] = {}
    if checkpointer is not None:
        compile_kwargs["checkpointer"] = checkpointer

    graph = builder.compile(**compile_kwargs)
    logger.info("[AutonomousGraph] Package 8 autonomous pipeline compiled — 10 nodes")
    return graph


def get_autonomous_graph_ascii() -> str:
    """Return ASCII diagram of the autonomous reporting pipeline."""
    return """
SFC AUTONOMOUS REPORTING PIPELINE (Package 8)
==============================================

  [START]
     │
     ▼
┌────────────────┐
│ scheduler_node │  ← Captures scheduler health; evaluates event-based triggers
└────────────────┘
     │
     ▼
┌────────────────────────┐
│ autonomous_trigger_node│  ← Fires autonomous workflows when conditions met
└────────────────────────┘
     │
     ▼
┌─────────────────────────┐
│ autonomous_execution_node│  ← Dispatches trigger-fired requests to main pipeline
└─────────────────────────┘
     │ (fan-out — all 4 run concurrently)
     ├──────────────────────────────────────────────────┐
     │                    │                    │        │
     ▼                    ▼                    ▼        ▼
┌──────────────┐  ┌───────────────┐  ┌──────────────┐  ┌──────────────────┐
│ executive_   │  │ operational_  │  │ historical_  │  │ cost_forecasting │
│ reporting_   │  │ reporting_    │  │ analytics_   │  │ _node            │
│ node         │  │ node          │  │ node         │  │                  │
└──────────────┘  └───────────────┘  └──────────────┘  └──────────────────┘
     │                    │                    │                    │
     └────────────────────┴────────────────────┴────────────────────┘
                                    │ (fan-in)
                                    ▼
                       ┌────────────────────────┐
                       │  batch_processing_node  │  ← Executes batch items from payload
                       └────────────────────────┘
                                    │
                                    ▼
                       ┌────────────────────────┐
                       │  report_delivery_node   │  ← Dashboard / Markdown / JSON / Email /
                       └────────────────────────┘    Telegram / WhatsApp
                                    │
                                    ▼
                          ┌───────────────┐
                          │ memory_update │  ← Persists cycle results + lessons
                          └───────────────┘
                                    │
                                  [END]

GOVERNANCE: Any content publishing triggered autonomously MUST route through
the main pipeline graph (graph.py) which enforces the governance gate.
Autonomous triggers fire the main pipeline — they never bypass it.
"""
