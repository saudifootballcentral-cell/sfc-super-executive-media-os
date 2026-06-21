"""End-to-end integration tests for Package 8C — Narrative Intelligence & Audience Modeling."""

import pytest

from sfc.graph.state import SFCState, make_initial_state
from sfc.events.types import (
    NarrativeForecastGenerated,
    NarrativeRiskDetected,
    AudienceSegmentUpdated,
    AudienceBehaviorChanged,
    InfluenceNetworkUpdated,
    ReactionSimulationCompleted,
    NarrativeStrategyRecommended,
    NarrativeEscalationTriggered,
)


# ---------------------------------------------------------------------------
# State initialization
# ---------------------------------------------------------------------------

class TestStateInitialization:
    def test_pkg8c_fields_in_state(self):
        state = make_initial_state("test", {})
        assert "narrative_models" in state
        assert "narrative_lifecycle" in state
        assert "narrative_forecast" in state
        assert "narrative_risk" in state
        assert "audience_models" in state
        assert "audience_segments" in state
        assert "audience_evolution" in state
        assert "influence_network" in state
        assert "reaction_forecast" in state
        assert "narrative_strategy" in state
        assert "narrative_command_center" in state

    def test_pkg8c_fields_initialized_empty(self):
        state = make_initial_state("test", {})
        assert state["narrative_models"] == {}
        assert state["narrative_lifecycle"] == {}
        assert state["narrative_forecast"] == {}
        assert state["narrative_risk"] == {}
        assert state["audience_models"] == {}
        assert state["audience_segments"] == {}
        assert state["audience_evolution"] == {}
        assert state["influence_network"] == {}
        assert state["reaction_forecast"] == {}
        assert state["narrative_strategy"] == {}
        assert state["narrative_command_center"] == {}


# ---------------------------------------------------------------------------
# Event types
# ---------------------------------------------------------------------------

class TestPkg8CEventTypes:
    def test_narrative_forecast_generated(self):
        e = NarrativeForecastGenerated(
            division="narrative",
            run_id="run_001",
            payload={"narrative_id": "n_001"},
        )
        assert e.event_type == "narrative_forecast_generated"

    def test_narrative_risk_detected(self):
        e = NarrativeRiskDetected(
            division="narrative",
            run_id="run_002",
            payload={"risk_level": "HIGH"},
        )
        assert e.event_type == "narrative_risk_detected"

    def test_audience_segment_updated(self):
        e = AudienceSegmentUpdated(
            division="audience",
            run_id="run_003",
            payload={"segment": "hardcore_fans"},
        )
        assert e.event_type == "audience_segment_updated"

    def test_audience_behavior_changed(self):
        e = AudienceBehaviorChanged(
            division="audience",
            run_id="run_004",
            payload={},
        )
        assert e.event_type == "audience_behavior_changed"

    def test_influence_network_updated(self):
        e = InfluenceNetworkUpdated(
            division="influence",
            run_id="run_005",
            payload={"nodes": 12},
        )
        assert e.event_type == "influence_network_updated"

    def test_reaction_simulation_completed(self):
        e = ReactionSimulationCompleted(
            division="simulation",
            run_id="run_006",
            payload={"scenario": "match_win"},
        )
        assert e.event_type == "reaction_simulation_completed"

    def test_narrative_strategy_recommended(self):
        e = NarrativeStrategyRecommended(
            division="narrative",
            run_id="run_007",
            payload={"action": "AMPLIFY"},
        )
        assert e.event_type == "narrative_strategy_recommended"

    def test_narrative_escalation_triggered(self):
        e = NarrativeEscalationTriggered(
            division="narrative",
            run_id="run_008",
            payload={"requires_war_room": True},
        )
        assert e.event_type == "narrative_escalation_triggered"

    def test_event_type_map_includes_pkg8c(self):
        from sfc.events.types import EVENT_TYPE_MAP
        assert "narrative_forecast_generated" in EVENT_TYPE_MAP
        assert "narrative_risk_detected" in EVENT_TYPE_MAP
        assert "audience_segment_updated" in EVENT_TYPE_MAP
        assert "audience_behavior_changed" in EVENT_TYPE_MAP
        assert "influence_network_updated" in EVENT_TYPE_MAP
        assert "reaction_simulation_completed" in EVENT_TYPE_MAP
        assert "narrative_strategy_recommended" in EVENT_TYPE_MAP
        assert "narrative_escalation_triggered" in EVENT_TYPE_MAP


# ---------------------------------------------------------------------------
# LangGraph node tests
# ---------------------------------------------------------------------------

class TestNarrativeModelingNode:
    @pytest.mark.asyncio
    async def test_node_returns_dict(self):
        from sfc.graph.nodes.narrative_modeling_node import narrative_modeling_node
        state = make_initial_state("test", {})
        result = await narrative_modeling_node(state)
        assert isinstance(result, dict)
        assert "narrative_models" in result
        assert result["pipeline_stage"] == "narrative_modeling"

    @pytest.mark.asyncio
    async def test_node_non_fatal_on_error(self):
        from sfc.graph.nodes.narrative_modeling_node import narrative_modeling_node
        result = await narrative_modeling_node({})
        assert "narrative_models" in result


class TestNarrativeLifecycleNode:
    @pytest.mark.asyncio
    async def test_node_returns_dict(self):
        from sfc.graph.nodes.narrative_lifecycle_node import narrative_lifecycle_node
        state = make_initial_state("test", {})
        result = await narrative_lifecycle_node(state)
        assert isinstance(result, dict)
        assert "narrative_lifecycle" in result
        assert result["pipeline_stage"] == "narrative_lifecycle"


class TestNarrativeForecastingNode:
    @pytest.mark.asyncio
    async def test_node_returns_dict(self):
        from sfc.graph.nodes.narrative_forecasting_node import narrative_forecasting_node
        state = make_initial_state("test", {})
        result = await narrative_forecasting_node(state)
        assert isinstance(result, dict)
        assert "narrative_forecast" in result
        assert result["pipeline_stage"] == "narrative_forecasting"


class TestNarrativeRiskNode:
    @pytest.mark.asyncio
    async def test_node_returns_dict(self):
        from sfc.graph.nodes.narrative_risk_node import narrative_risk_node
        state = make_initial_state("test", {})
        result = await narrative_risk_node(state)
        assert isinstance(result, dict)
        assert "narrative_risk" in result
        assert result["pipeline_stage"] == "narrative_risk"


class TestNarrativeStrategyNode:
    @pytest.mark.asyncio
    async def test_node_returns_dict(self):
        from sfc.graph.nodes.narrative_strategy_node import narrative_strategy_node
        state = make_initial_state("test", {})
        result = await narrative_strategy_node(state)
        assert isinstance(result, dict)
        assert "narrative_strategy" in result
        assert result["pipeline_stage"] == "narrative_strategy"


class TestAudienceModelingNode:
    @pytest.mark.asyncio
    async def test_node_returns_dict(self):
        from sfc.graph.nodes.audience_modeling_node import audience_modeling_node
        state = make_initial_state("test", {})
        result = await audience_modeling_node(state)
        assert isinstance(result, dict)
        assert "audience_models" in result
        assert result["pipeline_stage"] == "audience_modeling"


class TestAudienceSegmentationNode:
    @pytest.mark.asyncio
    async def test_node_returns_dict(self):
        from sfc.graph.nodes.audience_segmentation_node import audience_segmentation_node
        state = make_initial_state("test", {})
        result = await audience_segmentation_node(state)
        assert isinstance(result, dict)
        assert "audience_segments" in result
        assert result["pipeline_stage"] == "audience_segmentation"


class TestAudienceEvolutionNode:
    @pytest.mark.asyncio
    async def test_node_returns_dict(self):
        from sfc.graph.nodes.audience_evolution_node import audience_evolution_node
        state = make_initial_state("test", {})
        result = await audience_evolution_node(state)
        assert isinstance(result, dict)
        assert "audience_evolution" in result
        assert result["pipeline_stage"] == "audience_evolution"


class TestInfluenceNetworkNode:
    @pytest.mark.asyncio
    async def test_node_returns_dict(self):
        from sfc.graph.nodes.influence_network_node import influence_network_node
        state = make_initial_state("test", {})
        result = await influence_network_node(state)
        assert isinstance(result, dict)
        assert "influence_network" in result
        assert result["pipeline_stage"] == "influence_network"


class TestReactionSimulatorNode:
    @pytest.mark.asyncio
    async def test_node_returns_dict(self):
        from sfc.graph.nodes.reaction_simulator_node import reaction_simulator_node
        state = make_initial_state("test", {"context": {"scenario": "match_win"}})
        result = await reaction_simulator_node(state)
        assert isinstance(result, dict)
        assert "reaction_forecast" in result
        assert result["pipeline_stage"] == "reaction_simulator"

    @pytest.mark.asyncio
    async def test_node_unknown_scenario_defaults(self):
        from sfc.graph.nodes.reaction_simulator_node import reaction_simulator_node
        state = make_initial_state("test", {})
        state["context"] = {"scenario": "unknown_scenario_xyz"}
        result = await reaction_simulator_node(state)
        assert "reaction_forecast" in result


class TestNarrativeCommandCenterNode:
    @pytest.mark.asyncio
    async def test_node_returns_dict(self):
        from sfc.graph.nodes.narrative_command_center_node import narrative_command_center_node
        state = make_initial_state("test", {})
        result = await narrative_command_center_node(state)
        assert isinstance(result, dict)
        assert "narrative_command_center" in result
        assert result["pipeline_stage"] == "narrative_command_center"


# ---------------------------------------------------------------------------
# Command center integration
# ---------------------------------------------------------------------------

class TestNarrativeCommandCenter:
    @pytest.mark.asyncio
    async def test_run_full_intelligence(self):
        from sfc.narrative.command_center import NarrativeCommandCenter
        center = NarrativeCommandCenter()
        result = await center.run_full_intelligence()
        assert isinstance(result, dict)
        assert "narrative_map" in result
        assert "audience_model_report" in result
        assert "influence_network" in result

    @pytest.mark.asyncio
    async def test_simulate_scenario(self):
        from sfc.narrative.command_center import NarrativeCommandCenter
        center = NarrativeCommandCenter()
        result = await center.simulate_scenario("match_win", narrative_id="n_001")
        assert isinstance(result, dict)
        assert "forecast_id" in result

    @pytest.mark.asyncio
    async def test_simulate_unknown_scenario(self):
        from sfc.narrative.command_center import NarrativeCommandCenter
        center = NarrativeCommandCenter()
        result = await center.simulate_scenario("unknown_xyz")
        assert isinstance(result, dict)

    def test_get_status(self):
        from sfc.narrative.command_center import NarrativeCommandCenter
        center = NarrativeCommandCenter()
        status = center.get_status()
        assert status["status"] == "active"
        assert "engines" in status
        assert len(status["engines"]) == 10

    def test_singleton(self):
        from sfc.narrative.command_center import get_narrative_command_center
        a = get_narrative_command_center()
        b = get_narrative_command_center()
        assert a is b

    @pytest.mark.asyncio
    async def test_full_intelligence_summary(self):
        from sfc.narrative.command_center import NarrativeCommandCenter
        center = NarrativeCommandCenter()
        result = await center.run_full_intelligence()
        assert isinstance(result.get("summary"), str)
        assert len(result["summary"]) > 0

    @pytest.mark.asyncio
    async def test_full_intelligence_war_room_escalations(self):
        from sfc.narrative.command_center import NarrativeCommandCenter
        center = NarrativeCommandCenter()
        result = await center.run_full_intelligence()
        assert isinstance(result.get("war_room_escalations"), list)
