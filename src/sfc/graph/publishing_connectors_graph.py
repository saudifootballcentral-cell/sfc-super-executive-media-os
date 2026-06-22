"""Publishing & Intelligence Connectors Graph — Package 9A LangGraph pipeline.

This graph connects SFC to real-world platforms. It runs AFTER the Creative
Production Graph (8E) and AFTER the main pipeline governance gate has set
`ready_to_publish = True` on content packages.

Execution order
---------------
youtube_connector_node    Publish YouTube videos/Shorts + read channel analytics
  → x_connector_node      Publish X posts/threads + social intelligence feed
  → buffer_connector_node Route remaining packages through Buffer hub
  → analytics_sync_node   Aggregate cross-platform analytics + update history
  → END

Governance requirement
----------------------
Only packages with `ready_to_publish = True` (set by governance gate) are
published. This graph NEVER bypasses Constitution, Governance, Executive
Approval, or Publishing Controls.

Social Intelligence feed
------------------------
x_connector_node writes live trend data back to `trend_radar_data` so that
packages 8B and 8C can consume real platform signals on the next cycle.
"""

from __future__ import annotations

import logging
from typing import Any

from langgraph.graph import END, START, StateGraph

from sfc.graph.nodes.youtube_connector_node import youtube_connector_node
from sfc.graph.nodes.x_connector_node import x_connector_node
from sfc.graph.nodes.buffer_connector_node import buffer_connector_node
from sfc.graph.nodes.analytics_sync_node import analytics_sync_node

logger = logging.getLogger("sfc.graph.publishing_connectors")


def build_publishing_connectors_graph(checkpointer=None) -> StateGraph:
    """Build and compile the Package 9A Publishing Connectors LangGraph pipeline."""
    from sfc.graph.state import SFCState

    builder = StateGraph(SFCState)

    builder.add_node("youtube_connector", youtube_connector_node)
    builder.add_node("x_connector", x_connector_node)
    builder.add_node("buffer_connector", buffer_connector_node)
    builder.add_node("analytics_sync", analytics_sync_node)

    builder.add_edge(START, "youtube_connector")
    builder.add_edge("youtube_connector", "x_connector")
    builder.add_edge("x_connector", "buffer_connector")
    builder.add_edge("buffer_connector", "analytics_sync")
    builder.add_edge("analytics_sync", END)

    kwargs: dict[str, Any] = {}
    if checkpointer is not None:
        kwargs["checkpointer"] = checkpointer

    return builder.compile(**kwargs)


def get_publishing_connectors_graph_ascii() -> str:
    return (
        "Publishing Connectors Graph (Package 9A)\n"
        "─────────────────────────────────────────\n"
        "START\n"
        "  → youtube_connector    Upload videos/Shorts + channel analytics\n"
        "  → x_connector          Post threads + social intelligence feed\n"
        "  → buffer_connector     Route to Instagram/Threads/Facebook/TikTok\n"
        "  → analytics_sync       Aggregate metrics + update historical store\n"
        "END\n"
        "\n"
        "Governance: only packages with ready_to_publish=True are published\n"
        "Social feed: x_connector writes live trends → trend_radar_data (8B/8C)\n"
        "Secrets: YOUTUBE_CLIENT_ID/SECRET, X_API_KEY/SECRET, BUFFER_ACCESS_TOKEN\n"
    )
