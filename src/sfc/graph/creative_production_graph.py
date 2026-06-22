"""Creative Production Graph — Package 8E LangGraph pipeline.

This graph transforms intelligence into multimedia content assets.
It runs after the Social Intelligence Graph (8D) and feeds the main
publishing pipeline.

Execution order
---------------
creative_production_node     (orchestrator: build production plan)
  → image_factory_node       (generate branded images)
  → video_factory_node       (generate short-form video)
  → thumbnail_factory_node   (generate CTR-optimised thumbnails)
  → audio_factory_node       (generate Arabic/English audio)
  → shorts_factory_node      (generate TikTok/Reels/Shorts packages)
  → podcast_factory_node     (generate full podcast episode)
  → asset_management_node    (register all assets in registry)
  → quality_control_node     (5-point QC check on all assets)
  → content_packaging_node   (assemble platform-ready packages)
  → END

Governance requirement
----------------------
All content packages have `requires_approval = True` and
`governance_cleared = False` until the main pipeline governance gate
signs off.  This graph NEVER bypasses Constitution, Governance,
Executive Approval, or Publishing Controls.
"""

from __future__ import annotations

import logging
from typing import Any

from langgraph.graph import END, START, StateGraph

from sfc.graph.nodes.creative_production_node import creative_production_node
from sfc.graph.nodes.image_factory_node import image_factory_node
from sfc.graph.nodes.video_factory_node import video_factory_node
from sfc.graph.nodes.thumbnail_factory_node import thumbnail_factory_node
from sfc.graph.nodes.audio_factory_node import audio_factory_node
from sfc.graph.nodes.shorts_factory_node import shorts_factory_node
from sfc.graph.nodes.podcast_factory_node import podcast_factory_node
from sfc.graph.nodes.asset_management_node import asset_management_node
from sfc.graph.nodes.quality_control_node import quality_control_node
from sfc.graph.nodes.content_packaging_node import content_packaging_node

logger = logging.getLogger("sfc.graph.creative_production")


def build_creative_production_graph(checkpointer=None) -> StateGraph:
    """Build and compile the Package 8E Creative Production LangGraph pipeline."""
    from sfc.graph.state import SFCState

    builder = StateGraph(SFCState)

    # Register all 10 nodes
    builder.add_node("creative_production", creative_production_node)
    builder.add_node("image_factory", image_factory_node)
    builder.add_node("video_factory", video_factory_node)
    builder.add_node("thumbnail_factory", thumbnail_factory_node)
    builder.add_node("audio_factory", audio_factory_node)
    builder.add_node("shorts_factory", shorts_factory_node)
    builder.add_node("podcast_factory", podcast_factory_node)
    builder.add_node("asset_management", asset_management_node)
    builder.add_node("quality_control", quality_control_node)
    builder.add_node("content_packaging", content_packaging_node)

    # Sequential pipeline
    builder.add_edge(START, "creative_production")
    builder.add_edge("creative_production", "image_factory")
    builder.add_edge("image_factory", "video_factory")
    builder.add_edge("video_factory", "thumbnail_factory")
    builder.add_edge("thumbnail_factory", "audio_factory")
    builder.add_edge("audio_factory", "shorts_factory")
    builder.add_edge("shorts_factory", "podcast_factory")
    builder.add_edge("podcast_factory", "asset_management")
    builder.add_edge("asset_management", "quality_control")
    builder.add_edge("quality_control", "content_packaging")
    builder.add_edge("content_packaging", END)

    kwargs: dict[str, Any] = {}
    if checkpointer is not None:
        kwargs["checkpointer"] = checkpointer

    return builder.compile(**kwargs)


def get_creative_production_graph_ascii() -> str:
    return (
        "Creative Production Graph (Package 8E)\n"
        "─────────────────────────────────────────\n"
        "START\n"
        "  → creative_production   (orchestrator: production plan)\n"
        "  → image_factory         (GPT Image / Flux / Ideogram)\n"
        "  → video_factory         (Google Veo / Kling / Runway)\n"
        "  → thumbnail_factory     (A/B/C/D CTR variants)\n"
        "  → audio_factory         (ElevenLabs / Azure Voice)\n"
        "  → shorts_factory        (TikTok / Reels / YT Shorts)\n"
        "  → podcast_factory       (full AI episode + segments)\n"
        "  → asset_management      (registry + lifecycle)\n"
        "  → quality_control       (5-point brand/QC checks)\n"
        "  → content_packaging     (platform-ready bundles)\n"
        "END\n"
        "\n"
        "Governance: all packages require_approval=True\n"
        "           governance_cleared=False until main pipeline gate\n"
    )
