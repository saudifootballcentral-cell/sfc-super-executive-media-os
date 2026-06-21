"""Package 8D end-to-end integration tests — Social & Narrative Intelligence Graph."""

from __future__ import annotations

import pytest

from sfc.graph.state import make_initial_state


# ---------------------------------------------------------------------------
# Graph compilation
# ---------------------------------------------------------------------------

class TestGraphCompilation:
    def test_build_function_importable(self):
        from sfc.graph.social_intelligence_graph import build_social_intelligence_graph
        assert callable(build_social_intelligence_graph)

    def test_graph_compiles_without_checkpointer(self):
        from sfc.graph.social_intelligence_graph import build_social_intelligence_graph
        graph = build_social_intelligence_graph()
        assert graph is not None

    def test_graph_compiles_with_none_checkpointer(self):
        from sfc.graph.social_intelligence_graph import build_social_intelligence_graph
        graph = build_social_intelligence_graph(checkpointer=None)
        assert graph is not None

    def test_ascii_diagram_importable(self):
        from sfc.graph.social_intelligence_graph import get_social_intelligence_graph_ascii
        assert callable(get_social_intelligence_graph_ascii)

    def test_ascii_diagram_returns_string(self):
        from sfc.graph.social_intelligence_graph import get_social_intelligence_graph_ascii
        diagram = get_social_intelligence_graph_ascii()
        assert isinstance(diagram, str)
        assert len(diagram) > 100

    def test_ascii_diagram_contains_all_stages(self):
        from sfc.graph.social_intelligence_graph import get_social_intelligence_graph_ascii
        diagram = get_social_intelligence_graph_ascii()
        assert "social_intelligence" in diagram
        assert "trend_radar" in diagram
        assert "fan_sentiment" in diagram
        assert "narrative_intelligence" in diagram
        assert "narrative_modeling" in diagram
        assert "narrative_command_center" in diagram
        assert "memory_update" in diagram

    def test_ascii_diagram_has_governance_note(self):
        from sfc.graph.social_intelligence_graph import get_social_intelligence_graph_ascii
        diagram = get_social_intelligence_graph_ascii()
        assert "READ-ONLY" in diagram or "GOVERNANCE" in diagram


# ---------------------------------------------------------------------------
# Node registration
# ---------------------------------------------------------------------------

class TestNodeRegistration:
    """All 21 nodes must be registered in the compiled graph."""

    def _get_node_names(self):
        from sfc.graph.social_intelligence_graph import build_social_intelligence_graph
        graph = build_social_intelligence_graph()
        return set(graph.nodes)

    def test_package_8b_social_intelligence_registered(self):
        assert "social_intelligence" in self._get_node_names()

    def test_package_8b_trend_radar_registered(self):
        assert "trend_radar" in self._get_node_names()

    def test_package_8b_fan_sentiment_registered(self):
        assert "fan_sentiment" in self._get_node_names()

    def test_package_8b_narrative_intelligence_registered(self):
        assert "narrative_intelligence" in self._get_node_names()

    def test_package_8b_influencer_intelligence_registered(self):
        assert "influencer_intelligence" in self._get_node_names()

    def test_package_8b_virality_prediction_registered(self):
        assert "virality_prediction" in self._get_node_names()

    def test_package_8b_audience_intelligence_registered(self):
        assert "audience_intelligence" in self._get_node_names()

    def test_package_8b_opportunity_detection_registered(self):
        assert "opportunity_detection" in self._get_node_names()

    def test_package_8b_social_war_room_registered(self):
        assert "social_war_room" in self._get_node_names()

    def test_package_8c_narrative_modeling_registered(self):
        assert "narrative_modeling" in self._get_node_names()

    def test_package_8c_narrative_lifecycle_registered(self):
        # registered as narrative_lifecycle_step to avoid SFCState key clash
        assert "narrative_lifecycle_step" in self._get_node_names()

    def test_package_8c_narrative_forecasting_registered(self):
        assert "narrative_forecasting" in self._get_node_names()

    def test_package_8c_narrative_risk_registered(self):
        # registered as narrative_risk_step to avoid SFCState key clash
        assert "narrative_risk_step" in self._get_node_names()

    def test_package_8c_narrative_strategy_registered(self):
        # registered as narrative_strategy_step to avoid SFCState key clash
        assert "narrative_strategy_step" in self._get_node_names()

    def test_package_8c_audience_modeling_registered(self):
        assert "audience_modeling" in self._get_node_names()

    def test_package_8c_audience_segmentation_registered(self):
        assert "audience_segmentation" in self._get_node_names()

    def test_package_8c_audience_evolution_registered(self):
        # registered as audience_evolution_step to avoid SFCState key clash
        assert "audience_evolution_step" in self._get_node_names()

    def test_package_8c_influence_network_registered(self):
        # registered as influence_network_step to avoid SFCState key clash
        assert "influence_network_step" in self._get_node_names()

    def test_package_8c_reaction_simulator_registered(self):
        assert "reaction_simulator" in self._get_node_names()

    def test_package_8c_narrative_command_center_registered(self):
        # registered as narrative_command_center_step to avoid SFCState key clash
        assert "narrative_command_center_step" in self._get_node_names()

    def test_shared_memory_update_registered(self):
        assert "memory_update" in self._get_node_names()

    def test_total_node_count(self):
        names = self._get_node_names()
        # 9 Package 8B + 11 Package 8C + 1 memory_update = 21 nodes
        # LangGraph adds __start__ internally; filter those out
        user_nodes = {n for n in names if not n.startswith("__")}
        assert len(user_nodes) == 21


# ---------------------------------------------------------------------------
# Import resolution — all 8B and 8C nodes must import cleanly
# ---------------------------------------------------------------------------

class TestNodeImports:
    def test_import_social_intelligence_node(self):
        from sfc.graph.nodes.social_intelligence_node import social_intelligence_node
        assert callable(social_intelligence_node)

    def test_import_trend_radar_node(self):
        from sfc.graph.nodes.trend_radar_node import trend_radar_node
        assert callable(trend_radar_node)

    def test_import_fan_sentiment_node(self):
        from sfc.graph.nodes.fan_sentiment_node import fan_sentiment_node
        assert callable(fan_sentiment_node)

    def test_import_narrative_intelligence_node(self):
        from sfc.graph.nodes.narrative_intelligence_node import narrative_intelligence_node
        assert callable(narrative_intelligence_node)

    def test_import_influencer_intelligence_node(self):
        from sfc.graph.nodes.influencer_intelligence_node import influencer_intelligence_node
        assert callable(influencer_intelligence_node)

    def test_import_virality_prediction_node(self):
        from sfc.graph.nodes.virality_prediction_node import virality_prediction_node
        assert callable(virality_prediction_node)

    def test_import_audience_intelligence_node(self):
        from sfc.graph.nodes.audience_intelligence_node import audience_intelligence_node
        assert callable(audience_intelligence_node)

    def test_import_opportunity_detection_node(self):
        from sfc.graph.nodes.opportunity_detection_node import opportunity_detection_node
        assert callable(opportunity_detection_node)

    def test_import_social_war_room_node(self):
        from sfc.graph.nodes.social_war_room_node import social_war_room_node
        assert callable(social_war_room_node)

    def test_import_narrative_modeling_node(self):
        from sfc.graph.nodes.narrative_modeling_node import narrative_modeling_node
        assert callable(narrative_modeling_node)

    def test_import_narrative_lifecycle_node(self):
        from sfc.graph.nodes.narrative_lifecycle_node import narrative_lifecycle_node
        assert callable(narrative_lifecycle_node)

    def test_import_narrative_forecasting_node(self):
        from sfc.graph.nodes.narrative_forecasting_node import narrative_forecasting_node
        assert callable(narrative_forecasting_node)

    def test_import_narrative_risk_node(self):
        from sfc.graph.nodes.narrative_risk_node import narrative_risk_node
        assert callable(narrative_risk_node)

    def test_import_narrative_strategy_node(self):
        from sfc.graph.nodes.narrative_strategy_node import narrative_strategy_node
        assert callable(narrative_strategy_node)

    def test_import_audience_modeling_node(self):
        from sfc.graph.nodes.audience_modeling_node import audience_modeling_node
        assert callable(audience_modeling_node)

    def test_import_audience_segmentation_node(self):
        from sfc.graph.nodes.audience_segmentation_node import audience_segmentation_node
        assert callable(audience_segmentation_node)

    def test_import_audience_evolution_node(self):
        from sfc.graph.nodes.audience_evolution_node import audience_evolution_node
        assert callable(audience_evolution_node)

    def test_import_influence_network_node(self):
        from sfc.graph.nodes.influence_network_node import influence_network_node
        assert callable(influence_network_node)

    def test_import_reaction_simulator_node(self):
        from sfc.graph.nodes.reaction_simulator_node import reaction_simulator_node
        assert callable(reaction_simulator_node)

    def test_import_narrative_command_center_node(self):
        from sfc.graph.nodes.narrative_command_center_node import narrative_command_center_node
        assert callable(narrative_command_center_node)

    def test_import_memory_update_node(self):
        from sfc.graph.nodes.memory_update import memory_update_node
        assert callable(memory_update_node)


# ---------------------------------------------------------------------------
# Graph invocation — end-to-end pipeline runs to completion
# ---------------------------------------------------------------------------

class TestGraphInvocation:
    @pytest.mark.asyncio
    async def test_graph_invokes_with_initial_state(self):
        from sfc.graph.social_intelligence_graph import build_social_intelligence_graph
        graph = build_social_intelligence_graph()
        initial = make_initial_state("social_intelligence_scan", {})
        result = await graph.ainvoke(initial)
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_graph_produces_8b_outputs(self):
        from sfc.graph.social_intelligence_graph import build_social_intelligence_graph
        graph = build_social_intelligence_graph()
        initial = make_initial_state("social_intelligence_scan", {})
        result = await graph.ainvoke(initial)
        assert "social_intelligence_report" in result or "trend_radar_data" in result

    @pytest.mark.asyncio
    async def test_graph_produces_8c_narrative_outputs(self):
        from sfc.graph.social_intelligence_graph import build_social_intelligence_graph
        graph = build_social_intelligence_graph()
        initial = make_initial_state("social_intelligence_scan", {})
        result = await graph.ainvoke(initial)
        assert "narrative_models" in result
        assert "narrative_lifecycle" in result
        assert "narrative_forecast" in result
        assert "narrative_risk" in result
        assert "narrative_strategy" in result

    @pytest.mark.asyncio
    async def test_graph_produces_8c_audience_outputs(self):
        from sfc.graph.social_intelligence_graph import build_social_intelligence_graph
        graph = build_social_intelligence_graph()
        initial = make_initial_state("social_intelligence_scan", {})
        result = await graph.ainvoke(initial)
        assert "audience_models" in result
        assert "audience_segments" in result
        assert "audience_evolution" in result

    @pytest.mark.asyncio
    async def test_graph_produces_influence_and_simulation_outputs(self):
        from sfc.graph.social_intelligence_graph import build_social_intelligence_graph
        graph = build_social_intelligence_graph()
        initial = make_initial_state("social_intelligence_scan", {})
        result = await graph.ainvoke(initial)
        assert "influence_network" in result
        assert "reaction_forecast" in result

    @pytest.mark.asyncio
    async def test_graph_produces_command_center_output(self):
        from sfc.graph.social_intelligence_graph import build_social_intelligence_graph
        graph = build_social_intelligence_graph()
        initial = make_initial_state("social_intelligence_scan", {})
        result = await graph.ainvoke(initial)
        assert "narrative_command_center" in result

    @pytest.mark.asyncio
    async def test_graph_result_is_not_empty_dict(self):
        from sfc.graph.social_intelligence_graph import build_social_intelligence_graph
        graph = build_social_intelligence_graph()
        initial = make_initial_state("social_intelligence_scan", {})
        result = await graph.ainvoke(initial)
        assert len(result) > 10

    @pytest.mark.asyncio
    async def test_graph_tolerates_empty_context(self):
        from sfc.graph.social_intelligence_graph import build_social_intelligence_graph
        graph = build_social_intelligence_graph()
        initial = make_initial_state("social_intelligence_scan", {})
        initial["context"] = {}
        result = await graph.ainvoke(initial)
        assert result is not None

    @pytest.mark.asyncio
    async def test_graph_tolerates_scenario_in_context(self):
        from sfc.graph.social_intelligence_graph import build_social_intelligence_graph
        graph = build_social_intelligence_graph()
        initial = make_initial_state("social_intelligence_scan", {})
        initial["context"] = {"scenario": "transfer_announcement", "team": "AlHilal"}
        result = await graph.ainvoke(initial)
        assert result is not None


# ---------------------------------------------------------------------------
# Governance — read-only pipeline assertions
# ---------------------------------------------------------------------------

class TestGovernanceConstraints:
    def test_graph_module_has_governance_docstring(self):
        import sfc.graph.social_intelligence_graph as mod
        assert mod.__doc__ is not None
        assert "READ-ONLY" in mod.__doc__ or "Governance" in mod.__doc__

    def test_graph_does_not_import_publishing_node(self):
        import sfc.graph.social_intelligence_graph as mod
        import inspect
        source = inspect.getsource(mod)
        # Publishing node must not be part of the intelligence pipeline
        assert "publishing_node" not in source
        assert "publish_node" not in source

    def test_graph_does_not_import_governance_node(self):
        import sfc.graph.social_intelligence_graph as mod
        import inspect
        source = inspect.getsource(mod)
        # Governance gate is for the main pipeline, not read-only intelligence
        assert "from sfc.graph.nodes.governance" not in source

    def test_war_room_escalations_require_main_pipeline(self):
        import sfc.graph.social_intelligence_graph as mod
        import inspect
        source = inspect.getsource(mod)
        # Pipeline description must reference governance/main pipeline for escalations
        assert "governance" in source.lower() or "main pipeline" in source.lower()

    @pytest.mark.asyncio
    async def test_graph_result_has_no_publish_flag(self):
        from sfc.graph.social_intelligence_graph import build_social_intelligence_graph
        graph = build_social_intelligence_graph()
        initial = make_initial_state("social_intelligence_scan", {})
        result = await graph.ainvoke(initial)
        assert result.get("published") is not True
        assert result.get("is_published") is not True


# ---------------------------------------------------------------------------
# Node sequencing sanity — outputs from earlier nodes available to later ones
# ---------------------------------------------------------------------------

class TestNodeSequencing:
    @pytest.mark.asyncio
    async def test_narrative_models_populated_before_lifecycle(self):
        from sfc.graph.social_intelligence_graph import build_social_intelligence_graph
        graph = build_social_intelligence_graph()
        initial = make_initial_state("social_intelligence_scan", {})
        result = await graph.ainvoke(initial)
        # narrative_lifecycle uses narrative_models; both should be dicts
        assert isinstance(result.get("narrative_models"), dict)
        assert isinstance(result.get("narrative_lifecycle"), dict)

    @pytest.mark.asyncio
    async def test_audience_segments_populated_before_evolution(self):
        from sfc.graph.social_intelligence_graph import build_social_intelligence_graph
        graph = build_social_intelligence_graph()
        initial = make_initial_state("social_intelligence_scan", {})
        result = await graph.ainvoke(initial)
        assert isinstance(result.get("audience_segments"), dict)
        assert isinstance(result.get("audience_evolution"), dict)

    @pytest.mark.asyncio
    async def test_command_center_output_is_dict(self):
        from sfc.graph.social_intelligence_graph import build_social_intelligence_graph
        graph = build_social_intelligence_graph()
        initial = make_initial_state("social_intelligence_scan", {})
        result = await graph.ainvoke(initial)
        cc = result.get("narrative_command_center")
        assert isinstance(cc, dict)
