"""Package 9A end-to-end integration tests — Publishing & Intelligence Connectors."""

from __future__ import annotations

import pytest

from sfc.graph.state import make_initial_state


# ---------------------------------------------------------------------------
# Graph compilation
# ---------------------------------------------------------------------------

class TestGraphCompilation:
    def test_build_function_importable(self):
        from sfc.graph.publishing_connectors_graph import build_publishing_connectors_graph
        assert callable(build_publishing_connectors_graph)

    def test_graph_compiles_without_checkpointer(self):
        from sfc.graph.publishing_connectors_graph import build_publishing_connectors_graph
        graph = build_publishing_connectors_graph()
        assert graph is not None

    def test_graph_compiles_with_none_checkpointer(self):
        from sfc.graph.publishing_connectors_graph import build_publishing_connectors_graph
        graph = build_publishing_connectors_graph(checkpointer=None)
        assert graph is not None

    def test_ascii_diagram_importable(self):
        from sfc.graph.publishing_connectors_graph import get_publishing_connectors_graph_ascii
        assert callable(get_publishing_connectors_graph_ascii)

    def test_ascii_diagram_contains_all_stages(self):
        from sfc.graph.publishing_connectors_graph import get_publishing_connectors_graph_ascii
        diagram = get_publishing_connectors_graph_ascii()
        for stage in ["youtube_connector", "x_connector", "buffer_connector", "analytics_sync"]:
            assert stage in diagram, f"Stage '{stage}' missing from ASCII diagram"

    def test_ascii_diagram_mentions_governance(self):
        from sfc.graph.publishing_connectors_graph import get_publishing_connectors_graph_ascii
        diagram = get_publishing_connectors_graph_ascii()
        assert "governance" in diagram.lower() or "ready_to_publish" in diagram.lower()


# ---------------------------------------------------------------------------
# Node registration
# ---------------------------------------------------------------------------

class TestNodeRegistration:
    def test_four_nodes_registered(self):
        from sfc.graph.publishing_connectors_graph import build_publishing_connectors_graph
        graph = build_publishing_connectors_graph()
        node_names = set(graph.get_graph().nodes.keys())
        expected = {"youtube_connector", "x_connector", "buffer_connector", "analytics_sync"}
        assert expected.issubset(node_names)

    def test_no_extra_nodes(self):
        from sfc.graph.publishing_connectors_graph import build_publishing_connectors_graph
        graph = build_publishing_connectors_graph()
        node_names = set(graph.get_graph().nodes.keys()) - {"__start__", "__end__"}
        assert len(node_names) == 4


# ---------------------------------------------------------------------------
# Node imports
# ---------------------------------------------------------------------------

class TestNodeImports:
    def test_youtube_connector_node_importable(self):
        from sfc.graph.nodes.youtube_connector_node import youtube_connector_node
        assert callable(youtube_connector_node)

    def test_x_connector_node_importable(self):
        from sfc.graph.nodes.x_connector_node import x_connector_node
        assert callable(x_connector_node)

    def test_buffer_connector_node_importable(self):
        from sfc.graph.nodes.buffer_connector_node import buffer_connector_node
        assert callable(buffer_connector_node)

    def test_analytics_sync_node_importable(self):
        from sfc.graph.nodes.analytics_sync_node import analytics_sync_node
        assert callable(analytics_sync_node)


# ---------------------------------------------------------------------------
# Service imports
# ---------------------------------------------------------------------------

class TestServiceImports:
    def test_youtube_service_importable(self):
        from sfc.connectors.youtube.service import get_youtube_service, YouTubeService
        assert callable(get_youtube_service)
        assert YouTubeService is not None

    def test_x_service_importable(self):
        from sfc.connectors.x.service import get_x_service, XService
        assert callable(get_x_service)
        assert XService is not None

    def test_buffer_service_importable(self):
        from sfc.connectors.buffer.service import get_buffer_service, BufferService
        assert callable(get_buffer_service)
        assert BufferService is not None

    def test_analytics_service_importable(self):
        from sfc.connectors.analytics.service import get_analytics_sync_service, AnalyticsSyncService
        assert callable(get_analytics_sync_service)
        assert AnalyticsSyncService is not None


# ---------------------------------------------------------------------------
# Model imports
# ---------------------------------------------------------------------------

class TestModelImports:
    def test_youtube_models_importable(self):
        from sfc.connectors.youtube.models import (
            VideoUploadRequest, VideoPublishResult, YouTubeAnalytics,
            ChannelMetrics, Playlist, YouTubeConnectorReport,
        )
        assert VideoUploadRequest is not None

    def test_x_models_importable(self):
        from sfc.connectors.x.models import (
            XPost, XThread, XMetrics, XTrend, XConversation, XConnectorReport,
        )
        assert XPost is not None

    def test_buffer_models_importable(self):
        from sfc.connectors.buffer.models import (
            BufferPost, BufferPublishResult, BufferQueue,
            BufferPlatform, BufferConnectorReport,
        )
        assert BufferPost is not None

    def test_analytics_models_importable(self):
        from sfc.connectors.analytics.models import (
            AnalyticsSnapshot, AnalyticsSyncReport, ConnectorObservability,
            Platform, MetricType, PlatformGrowth,
        )
        assert AnalyticsSnapshot is not None


# ---------------------------------------------------------------------------
# State keys
# ---------------------------------------------------------------------------

class TestStateKeys:
    def test_youtube_results_in_state(self):
        state = make_initial_state("publish", {})
        assert "youtube_results" in state
        assert state["youtube_results"] == {}

    def test_x_results_in_state(self):
        state = make_initial_state("publish", {})
        assert "x_results" in state
        assert state["x_results"] == {}

    def test_buffer_queue_state_in_state(self):
        state = make_initial_state("publish", {})
        assert "buffer_queue_state" in state
        assert state["buffer_queue_state"] == {}

    def test_analytics_data_in_state(self):
        state = make_initial_state("publish", {})
        assert "analytics_data" in state
        assert state["analytics_data"] == {}

    def test_content_packages_in_state(self):
        state = make_initial_state("publish", {})
        assert "content_packages" in state
        assert state["content_packages"] == []

    def test_trend_radar_data_in_state(self):
        state = make_initial_state("publish", {})
        assert "trend_radar_data" in state


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

class TestEvents:
    def test_video_published_event_importable(self):
        from sfc.events.types import VideoPublished
        assert VideoPublished is not None

    def test_analytics_updated_event_importable(self):
        from sfc.events.types import AnalyticsUpdated
        assert AnalyticsUpdated is not None

    def test_channel_growth_updated_event_importable(self):
        from sfc.events.types import ChannelGrowthUpdated
        assert ChannelGrowthUpdated is not None

    def test_x_post_published_event_importable(self):
        from sfc.events.types import XPostPublished
        assert XPostPublished is not None

    def test_x_thread_published_event_importable(self):
        from sfc.events.types import XThreadPublished
        assert XThreadPublished is not None

    def test_x_conversation_detected_event_importable(self):
        from sfc.events.types import XConversationDetected
        assert XConversationDetected is not None

    def test_buffer_post_created_event_importable(self):
        from sfc.events.types import BufferPostCreated
        assert BufferPostCreated is not None

    def test_buffer_post_published_event_importable(self):
        from sfc.events.types import BufferPostPublished
        assert BufferPostPublished is not None

    def test_buffer_post_failed_event_importable(self):
        from sfc.events.types import BufferPostFailed
        assert BufferPostFailed is not None

    def test_events_registered_in_event_type_map(self):
        from sfc.events.types import EVENT_TYPE_MAP
        expected = [
            "video_published", "analytics_updated", "channel_growth_updated",
            "x_post_published", "x_thread_published", "x_conversation_detected",
            "buffer_post_created", "buffer_post_published", "buffer_post_failed",
        ]
        for event_type in expected:
            assert event_type in EVENT_TYPE_MAP, f"Event '{event_type}' not in EVENT_TYPE_MAP"

    def test_video_published_event_instantiable(self):
        from sfc.events.types import VideoPublished
        e = VideoPublished(division="publishing", run_id="test-run")
        assert e.event_type == "video_published"
        assert e.division == "publishing"

    def test_x_post_published_event_instantiable(self):
        from sfc.events.types import XPostPublished
        e = XPostPublished(division="publishing", run_id="test-run")
        assert e.event_type == "x_post_published"
        assert e.division == "publishing"

    def test_buffer_post_created_event_instantiable(self):
        from sfc.events.types import BufferPostCreated
        e = BufferPostCreated(division="publishing", run_id="test-run")
        assert e.event_type == "buffer_post_created"
        assert e.division == "publishing"


# ---------------------------------------------------------------------------
# Graph invocation
# ---------------------------------------------------------------------------

class TestGraphInvocation:
    @pytest.mark.asyncio
    async def test_graph_runs_with_empty_packages(self):
        from sfc.graph.publishing_connectors_graph import build_publishing_connectors_graph
        graph = build_publishing_connectors_graph()
        state = make_initial_state("publish", {})
        result = await graph.ainvoke(state)
        assert result is not None

    @pytest.mark.asyncio
    async def test_graph_sets_pipeline_stage(self):
        from sfc.graph.publishing_connectors_graph import build_publishing_connectors_graph
        graph = build_publishing_connectors_graph()
        state = make_initial_state("publish", {})
        result = await graph.ainvoke(state)
        assert result["pipeline_stage"] == "analytics_sync"

    @pytest.mark.asyncio
    async def test_graph_populates_analytics_data(self):
        from sfc.graph.publishing_connectors_graph import build_publishing_connectors_graph
        graph = build_publishing_connectors_graph()
        state = make_initial_state("publish", {})
        result = await graph.ainvoke(state)
        assert isinstance(result["analytics_data"], dict)

    @pytest.mark.asyncio
    async def test_graph_populates_youtube_results(self):
        from sfc.graph.publishing_connectors_graph import build_publishing_connectors_graph
        graph = build_publishing_connectors_graph()
        state = make_initial_state("publish", {})
        result = await graph.ainvoke(state)
        assert isinstance(result["youtube_results"], dict)
        assert "channel_metrics" in result["youtube_results"]

    @pytest.mark.asyncio
    async def test_graph_populates_x_results(self):
        from sfc.graph.publishing_connectors_graph import build_publishing_connectors_graph
        graph = build_publishing_connectors_graph()
        state = make_initial_state("publish", {})
        result = await graph.ainvoke(state)
        assert isinstance(result["x_results"], dict)

    @pytest.mark.asyncio
    async def test_graph_populates_buffer_queue_state(self):
        from sfc.graph.publishing_connectors_graph import build_publishing_connectors_graph
        graph = build_publishing_connectors_graph()
        state = make_initial_state("publish", {})
        result = await graph.ainvoke(state)
        assert isinstance(result["buffer_queue_state"], dict)

    @pytest.mark.asyncio
    async def test_graph_with_youtube_packages(self):
        from sfc.graph.publishing_connectors_graph import build_publishing_connectors_graph
        graph = build_publishing_connectors_graph()
        state = make_initial_state("publish", {})
        state["content_packages"] = [
            {
                "package_type": "youtube_video",
                "title": "SPL Highlights",
                "description": "Round 15 highlights",
                "hashtags": ["#SPL", "#SaudiFootball"],
                "ready_to_publish": True,
                "governance_cleared": True,
                "quality_score": 85,
            }
        ]
        result = await graph.ainvoke(state)
        yt = result.get("youtube_results", {})
        assert len(yt.get("publish_results", [])) >= 1

    @pytest.mark.asyncio
    async def test_graph_with_x_thread_package(self):
        from sfc.graph.publishing_connectors_graph import build_publishing_connectors_graph
        graph = build_publishing_connectors_graph()
        state = make_initial_state("publish", {})
        state["content_packages"] = [
            {
                "package_type": "x_thread",
                "caption": "Breaking: Transfer news! #SFC",
                "hashtags": ["#AlHilal"],
                "ready_to_publish": True,
                "governance_cleared": True,
                "quality_score": 80,
            }
        ]
        result = await graph.ainvoke(state)
        x = result.get("x_results", {})
        assert len(x.get("publish_results", [])) >= 1


# ---------------------------------------------------------------------------
# Governance contract
# ---------------------------------------------------------------------------

class TestGovernanceContract:
    @pytest.mark.asyncio
    async def test_youtube_node_skips_uncleared_packages(self):
        from sfc.graph.nodes.youtube_connector_node import youtube_connector_node
        state = make_initial_state("publish", {})
        state["content_packages"] = [
            {
                "package_type": "youtube_video",
                "title": "Not approved",
                "ready_to_publish": False,
                "governance_cleared": False,
            }
        ]
        result = await youtube_connector_node(state)
        assert result["youtube_results"].get("publish_results", []) == []

    @pytest.mark.asyncio
    async def test_x_node_skips_uncleared_packages(self):
        from sfc.graph.nodes.x_connector_node import x_connector_node
        state = make_initial_state("publish", {})
        state["content_packages"] = [
            {
                "package_type": "x_thread",
                "caption": "Unapproved post",
                "ready_to_publish": False,
            }
        ]
        result = await x_connector_node(state)
        assert result["x_results"].get("publish_results", []) == []

    @pytest.mark.asyncio
    async def test_buffer_node_skips_uncleared_packages(self):
        from sfc.graph.nodes.buffer_connector_node import buffer_connector_node
        state = make_initial_state("publish", {})
        state["content_packages"] = [
            {
                "package_type": "instagram",
                "caption": "Unapproved Instagram post",
                "ready_to_publish": False,
            }
        ]
        result = await buffer_connector_node(state)
        assert result["buffer_queue_state"].get("publish_results", []) == []

    @pytest.mark.asyncio
    async def test_youtube_node_publishes_cleared_packages(self):
        from sfc.graph.nodes.youtube_connector_node import youtube_connector_node
        state = make_initial_state("publish", {})
        state["content_packages"] = [
            {
                "package_type": "youtube_video",
                "title": "Approved Video",
                "ready_to_publish": True,
                "governance_cleared": True,
                "quality_score": 90,
            }
        ]
        result = await youtube_connector_node(state)
        assert len(result["youtube_results"].get("publish_results", [])) == 1

    @pytest.mark.asyncio
    async def test_buffer_node_publishes_cleared_packages(self):
        from sfc.graph.nodes.buffer_connector_node import buffer_connector_node
        state = make_initial_state("publish", {})
        state["content_packages"] = [
            {
                "package_type": "instagram",
                "caption": "Approved Instagram post",
                "ready_to_publish": True,
                "governance_cleared": True,
                "quality_score": 80,
            }
        ]
        result = await buffer_connector_node(state)
        assert len(result["buffer_queue_state"].get("publish_results", [])) >= 1


# ---------------------------------------------------------------------------
# Social intelligence feed
# ---------------------------------------------------------------------------

class TestSocialIntelligenceFeed:
    @pytest.mark.asyncio
    async def test_x_node_writes_trend_radar_data(self):
        from sfc.graph.nodes.x_connector_node import x_connector_node
        state = make_initial_state("publish", {})
        result = await x_connector_node(state)
        assert "trend_radar_data" in result
        assert isinstance(result["trend_radar_data"], dict)

    @pytest.mark.asyncio
    async def test_x_node_trend_radar_has_live_trends(self):
        from sfc.graph.nodes.x_connector_node import x_connector_node
        state = make_initial_state("publish", {})
        result = await x_connector_node(state)
        trend_radar = result.get("trend_radar_data", {})
        assert "live_trends" in trend_radar
        assert len(trend_radar["live_trends"]) > 0

    @pytest.mark.asyncio
    async def test_x_node_trend_radar_has_top_trend(self):
        from sfc.graph.nodes.x_connector_node import x_connector_node
        state = make_initial_state("publish", {})
        result = await x_connector_node(state)
        trend_radar = result.get("trend_radar_data", {})
        assert "top_trend" in trend_radar
        assert trend_radar["top_trend"] != ""

    @pytest.mark.asyncio
    async def test_x_node_preserves_existing_trend_radar(self):
        from sfc.graph.nodes.x_connector_node import x_connector_node
        state = make_initial_state("publish", {})
        state["trend_radar_data"] = {"existing_key": "existing_value"}
        result = await x_connector_node(state)
        assert result["trend_radar_data"].get("existing_key") == "existing_value"

    @pytest.mark.asyncio
    async def test_x_results_has_social_intelligence(self):
        from sfc.graph.nodes.x_connector_node import x_connector_node
        state = make_initial_state("publish", {})
        result = await x_connector_node(state)
        x_results = result.get("x_results", {})
        assert "social_intelligence" in x_results
        si = x_results["social_intelligence"]
        assert "trending_topics" in si
        assert "keyword_trends" in si


# ---------------------------------------------------------------------------
# Analytics sync
# ---------------------------------------------------------------------------

class TestAnalyticsSyncIntegration:
    @pytest.mark.asyncio
    async def test_analytics_node_populates_data(self):
        from sfc.graph.nodes.analytics_sync_node import analytics_sync_node
        state = make_initial_state("publish", {})
        result = await analytics_sync_node(state)
        assert "analytics_data" in result
        data = result["analytics_data"]
        assert "total_views" in data
        assert "platforms_synced" in data

    @pytest.mark.asyncio
    async def test_analytics_node_updates_historical_analytics(self):
        from sfc.graph.nodes.analytics_sync_node import analytics_sync_node
        state = make_initial_state("publish", {})
        result = await analytics_sync_node(state)
        assert "historical_analytics" in result
        hist = result["historical_analytics"]
        assert "latest_sync" in hist
        assert "total_views_cumulative" in hist

    @pytest.mark.asyncio
    async def test_analytics_node_accumulates_views(self):
        from sfc.graph.nodes.analytics_sync_node import analytics_sync_node
        state = make_initial_state("publish", {})
        state["historical_analytics"] = {"total_views_cumulative": 500_000}
        result = await analytics_sync_node(state)
        hist = result["historical_analytics"]
        assert hist["total_views_cumulative"] >= 500_000

    @pytest.mark.asyncio
    async def test_analytics_node_syncs_youtube_video_ids(self):
        from sfc.graph.nodes.analytics_sync_node import analytics_sync_node
        state = make_initial_state("publish", {})
        state["youtube_results"] = {
            "publish_results": [{"video_id": "test_vid_1"}, {"video_id": "test_vid_2"}]
        }
        result = await analytics_sync_node(state)
        assert result["analytics_data"] != {}

    @pytest.mark.asyncio
    async def test_analytics_node_syncs_x_post_ids(self):
        from sfc.graph.nodes.analytics_sync_node import analytics_sync_node
        state = make_initial_state("publish", {})
        state["x_results"] = {
            "publish_results": [{"platform_post_id": "x_post_1"}]
        }
        result = await analytics_sync_node(state)
        assert result["analytics_data"] != {}

    @pytest.mark.asyncio
    async def test_full_graph_produces_analytics_report(self):
        from sfc.graph.publishing_connectors_graph import build_publishing_connectors_graph
        graph = build_publishing_connectors_graph()
        state = make_initial_state("publish", {})
        result = await graph.ainvoke(state)
        analytics = result.get("analytics_data", {})
        assert "total_views" in analytics
        assert len(analytics.get("platforms_synced", [])) >= 2
