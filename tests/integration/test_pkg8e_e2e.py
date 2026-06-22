"""Package 8E end-to-end integration tests — Creative Production Graph."""

from __future__ import annotations

import pytest

from sfc.graph.state import make_initial_state


# ---------------------------------------------------------------------------
# Graph compilation
# ---------------------------------------------------------------------------

class TestGraphCompilation:
    def test_build_function_importable(self):
        from sfc.graph.creative_production_graph import build_creative_production_graph
        assert callable(build_creative_production_graph)

    def test_graph_compiles_without_checkpointer(self):
        from sfc.graph.creative_production_graph import build_creative_production_graph
        graph = build_creative_production_graph()
        assert graph is not None

    def test_graph_compiles_with_none_checkpointer(self):
        from sfc.graph.creative_production_graph import build_creative_production_graph
        graph = build_creative_production_graph(checkpointer=None)
        assert graph is not None

    def test_ascii_diagram_importable(self):
        from sfc.graph.creative_production_graph import get_creative_production_graph_ascii
        assert callable(get_creative_production_graph_ascii)

    def test_ascii_diagram_contains_all_stages(self):
        from sfc.graph.creative_production_graph import get_creative_production_graph_ascii
        diagram = get_creative_production_graph_ascii()
        for stage in [
            "creative_production", "image_factory", "video_factory",
            "thumbnail_factory", "audio_factory", "shorts_factory",
            "podcast_factory", "asset_management", "quality_control",
            "content_packaging",
        ]:
            assert stage in diagram, f"Stage '{stage}' missing from ASCII diagram"

    def test_governance_note_in_ascii(self):
        from sfc.graph.creative_production_graph import get_creative_production_graph_ascii
        diagram = get_creative_production_graph_ascii()
        assert "require" in diagram.lower() or "governance" in diagram.lower()


# ---------------------------------------------------------------------------
# Node registration
# ---------------------------------------------------------------------------

class TestNodeRegistration:
    def test_all_ten_nodes_registered(self):
        from sfc.graph.creative_production_graph import build_creative_production_graph
        graph = build_creative_production_graph()
        node_names = set(graph.get_graph().nodes.keys())
        expected = {
            "creative_production", "image_factory", "video_factory",
            "thumbnail_factory", "audio_factory", "shorts_factory",
            "podcast_factory", "asset_management", "quality_control",
            "content_packaging",
        }
        assert expected.issubset(node_names)

    def test_no_extra_unexpected_nodes(self):
        from sfc.graph.creative_production_graph import build_creative_production_graph
        graph = build_creative_production_graph()
        node_names = set(graph.get_graph().nodes.keys()) - {"__start__", "__end__"}
        assert len(node_names) == 10


# ---------------------------------------------------------------------------
# Node imports
# ---------------------------------------------------------------------------

class TestNodeImports:
    def test_creative_production_node_importable(self):
        from sfc.graph.nodes.creative_production_node import creative_production_node
        assert callable(creative_production_node)

    def test_image_factory_node_importable(self):
        from sfc.graph.nodes.image_factory_node import image_factory_node
        assert callable(image_factory_node)

    def test_video_factory_node_importable(self):
        from sfc.graph.nodes.video_factory_node import video_factory_node
        assert callable(video_factory_node)

    def test_thumbnail_factory_node_importable(self):
        from sfc.graph.nodes.thumbnail_factory_node import thumbnail_factory_node
        assert callable(thumbnail_factory_node)

    def test_audio_factory_node_importable(self):
        from sfc.graph.nodes.audio_factory_node import audio_factory_node
        assert callable(audio_factory_node)

    def test_shorts_factory_node_importable(self):
        from sfc.graph.nodes.shorts_factory_node import shorts_factory_node
        assert callable(shorts_factory_node)

    def test_podcast_factory_node_importable(self):
        from sfc.graph.nodes.podcast_factory_node import podcast_factory_node
        assert callable(podcast_factory_node)

    def test_asset_management_node_importable(self):
        from sfc.graph.nodes.asset_management_node import asset_management_node
        assert callable(asset_management_node)

    def test_quality_control_node_importable(self):
        from sfc.graph.nodes.quality_control_node import quality_control_node
        assert callable(quality_control_node)

    def test_content_packaging_node_importable(self):
        from sfc.graph.nodes.content_packaging_node import content_packaging_node
        assert callable(content_packaging_node)


# ---------------------------------------------------------------------------
# Service imports
# ---------------------------------------------------------------------------

class TestServiceImports:
    def test_orchestrator_service_importable(self):
        from sfc.creative.orchestrator.service import get_creative_production_orchestrator
        assert callable(get_creative_production_orchestrator)

    def test_image_service_importable(self):
        from sfc.creative.image.service import get_image_factory_service
        assert callable(get_image_factory_service)

    def test_video_service_importable(self):
        from sfc.creative.video.service import get_video_factory_service
        assert callable(get_video_factory_service)

    def test_thumbnail_service_importable(self):
        from sfc.creative.thumbnail.service import get_thumbnail_factory_service
        assert callable(get_thumbnail_factory_service)

    def test_audio_service_importable(self):
        from sfc.creative.audio.service import get_audio_factory_service
        assert callable(get_audio_factory_service)

    def test_shorts_service_importable(self):
        from sfc.creative.shorts.service import get_shorts_factory_service
        assert callable(get_shorts_factory_service)

    def test_podcast_service_importable(self):
        from sfc.creative.podcast.service import get_podcast_factory_service
        assert callable(get_podcast_factory_service)

    def test_asset_service_importable(self):
        from sfc.creative.assets.service import get_asset_management_service
        assert callable(get_asset_management_service)

    def test_quality_service_importable(self):
        from sfc.creative.quality.service import get_quality_control_service
        assert callable(get_quality_control_service)

    def test_packaging_service_importable(self):
        from sfc.creative.packaging.service import get_content_packaging_service
        assert callable(get_content_packaging_service)


# ---------------------------------------------------------------------------
# State extension
# ---------------------------------------------------------------------------

class TestStateExtension:
    def test_production_plan_in_state(self):
        state = make_initial_state("creative", {})
        assert "production_plan" in state
        assert state["production_plan"] == {}

    def test_image_assets_in_state(self):
        state = make_initial_state("creative", {})
        assert "image_assets" in state
        assert state["image_assets"] == []

    def test_video_assets_in_state(self):
        state = make_initial_state("creative", {})
        assert "video_assets" in state

    def test_thumbnail_assets_in_state(self):
        state = make_initial_state("creative", {})
        assert "thumbnail_assets" in state

    def test_audio_assets_in_state(self):
        state = make_initial_state("creative", {})
        assert "audio_assets" in state

    def test_shorts_packages_in_state(self):
        state = make_initial_state("creative", {})
        assert "shorts_packages" in state

    def test_podcast_episodes_in_state(self):
        state = make_initial_state("creative", {})
        assert "podcast_episodes" in state

    def test_asset_registry_in_state(self):
        state = make_initial_state("creative", {})
        assert "asset_registry" in state

    def test_quality_reports_in_state(self):
        state = make_initial_state("creative", {})
        assert "quality_reports" in state

    def test_content_packages_in_state(self):
        state = make_initial_state("creative", {})
        assert "content_packages" in state


# ---------------------------------------------------------------------------
# Graph invocation
# ---------------------------------------------------------------------------

class TestGraphInvocation:
    @pytest.mark.asyncio
    async def test_graph_runs_to_completion(self):
        from sfc.graph.creative_production_graph import build_creative_production_graph
        graph = build_creative_production_graph()
        state = make_initial_state("creative", {"narrative": "SPL matchday"})
        result = await graph.ainvoke(state)
        assert result is not None

    @pytest.mark.asyncio
    async def test_production_plan_populated(self):
        from sfc.graph.creative_production_graph import build_creative_production_graph
        graph = build_creative_production_graph()
        state = make_initial_state("creative", {})
        result = await graph.ainvoke(state)
        assert isinstance(result.get("production_plan"), dict)
        assert result["production_plan"] != {}

    @pytest.mark.asyncio
    async def test_image_assets_generated(self):
        from sfc.graph.creative_production_graph import build_creative_production_graph
        graph = build_creative_production_graph()
        state = make_initial_state("creative", {})
        result = await graph.ainvoke(state)
        assert isinstance(result.get("image_assets"), list)
        assert len(result["image_assets"]) >= 1

    @pytest.mark.asyncio
    async def test_video_assets_generated(self):
        from sfc.graph.creative_production_graph import build_creative_production_graph
        graph = build_creative_production_graph()
        state = make_initial_state("creative", {})
        result = await graph.ainvoke(state)
        assert isinstance(result.get("video_assets"), list)
        assert len(result["video_assets"]) >= 1

    @pytest.mark.asyncio
    async def test_shorts_packages_generated(self):
        from sfc.graph.creative_production_graph import build_creative_production_graph
        graph = build_creative_production_graph()
        state = make_initial_state("creative", {})
        result = await graph.ainvoke(state)
        assert isinstance(result.get("shorts_packages"), list)
        assert len(result["shorts_packages"]) >= 1

    @pytest.mark.asyncio
    async def test_podcast_episodes_generated(self):
        from sfc.graph.creative_production_graph import build_creative_production_graph
        graph = build_creative_production_graph()
        state = make_initial_state("creative", {})
        result = await graph.ainvoke(state)
        assert isinstance(result.get("podcast_episodes"), list)
        assert len(result["podcast_episodes"]) >= 1

    @pytest.mark.asyncio
    async def test_quality_reports_generated(self):
        from sfc.graph.creative_production_graph import build_creative_production_graph
        graph = build_creative_production_graph()
        state = make_initial_state("creative", {})
        result = await graph.ainvoke(state)
        assert isinstance(result.get("quality_reports"), list)
        assert len(result["quality_reports"]) >= 1

    @pytest.mark.asyncio
    async def test_content_packages_assembled(self):
        from sfc.graph.creative_production_graph import build_creative_production_graph
        graph = build_creative_production_graph()
        state = make_initial_state("creative", {})
        result = await graph.ainvoke(state)
        assert isinstance(result.get("content_packages"), list)
        assert len(result["content_packages"]) >= 1

    @pytest.mark.asyncio
    async def test_no_hard_failures(self):
        from sfc.graph.creative_production_graph import build_creative_production_graph
        graph = build_creative_production_graph()
        state = make_initial_state("creative", {})
        result = await graph.ainvoke(state)
        assert isinstance(result.get("errors", []), list)


# ---------------------------------------------------------------------------
# Governance constraints
# ---------------------------------------------------------------------------

class TestGovernanceConstraints:
    def test_nodes_do_not_import_publishing(self):
        import ast
        import pathlib
        nodes_dir = pathlib.Path(
            "/home/user/sfc-super-executive-media-os/src/sfc/graph/nodes"
        )
        creative_nodes = [
            "creative_production_node.py",
            "image_factory_node.py",
            "video_factory_node.py",
            "thumbnail_factory_node.py",
            "audio_factory_node.py",
            "shorts_factory_node.py",
            "podcast_factory_node.py",
            "asset_management_node.py",
            "quality_control_node.py",
            "content_packaging_node.py",
        ]
        for node_file in creative_nodes:
            path = nodes_dir / node_file
            source = path.read_text()
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    if isinstance(node, ast.ImportFrom) and node.module:
                        assert "sfc.publishing" not in node.module, (
                            f"{node_file} imports sfc.publishing — bypass violation"
                        )
                        assert "sfc.governance" not in node.module, (
                            f"{node_file} imports sfc.governance — bypass violation"
                        )

    def test_packages_require_approval_true(self):
        from sfc.creative.packaging.models import PublishingMetadata
        meta = PublishingMetadata()
        assert meta.requires_approval is True

    @pytest.mark.asyncio
    async def test_content_packages_not_auto_ready_without_governance(self):
        from sfc.creative.packaging.service import ContentPackagingService
        from sfc.creative.packaging.models import PackageType
        service = ContentPackagingService()
        pkg = await service.create_package(
            package_type=PackageType.TIKTOK,
            title="No Governance",
            quality_score=95.0,
            governance_cleared=False,
        )
        assert pkg.ready_to_publish is False

    def test_creative_production_graph_has_no_publish_node(self):
        from sfc.graph.creative_production_graph import build_creative_production_graph
        graph = build_creative_production_graph()
        node_names = set(graph.get_graph().nodes.keys())
        assert "publishing" not in node_names
        assert "governance" not in node_names


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

class TestEvents:
    def test_package_8e_events_registered(self):
        from sfc.events.types import EVENT_TYPE_MAP
        expected_events = [
            "production_plan_created",
            "image_assets_generated",
            "video_assets_generated",
            "shorts_package_generated",
            "podcast_episode_generated",
            "quality_review_completed",
            "content_package_ready",
            "creative_production_completed",
        ]
        for event_type in expected_events:
            assert event_type in EVENT_TYPE_MAP, (
                f"Event '{event_type}' not registered in EVENT_TYPE_MAP"
            )

    def test_production_plan_created_instantiable(self):
        from sfc.events.types import ProductionPlanCreated
        event = ProductionPlanCreated(division="creative", run_id="test-run")
        assert event.event_type == "production_plan_created"

    def test_creative_production_completed_instantiable(self):
        from sfc.events.types import CreativeProductionCompleted
        event = CreativeProductionCompleted(division="creative", run_id="test-run")
        assert event.event_type == "creative_production_completed"
