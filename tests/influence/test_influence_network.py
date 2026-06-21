"""Tests for Influence Network Engine."""

import pytest

from sfc.influence.network.models import (
    InfluenceEdge,
    InfluenceNetwork,
    InfluenceNode,
    InfluenceNodeType,
    InfluenceRelationshipType,
    PropagationModel,
)
from sfc.influence.network.service import InfluenceNetworkEngine, get_influence_network_engine


class TestInfluenceNode:
    def _make_node(self, **kwargs) -> InfluenceNode:
        defaults = dict(
            name="Test Node",
            handle="@test",
            node_type=InfluenceNodeType.JOURNALIST,
            platforms=["x"],
            followers=100_000,
            influence_score=75.0,
            reach_score=70.0,
            credibility_score=80.0,
            velocity_score=60.0,
            narrative_affinities=["player"],
        )
        defaults.update(kwargs)
        return InfluenceNode(**defaults)

    def test_create(self):
        n = self._make_node()
        assert n.node_id != ""
        assert n.name == "Test Node"

    def test_network_centrality(self):
        n = self._make_node(influence_score=80.0, reach_score=70.0, credibility_score=60.0)
        expected = 80.0 * 0.4 + 70.0 * 0.3 + 60.0 * 0.3
        assert n.network_centrality == pytest.approx(expected, rel=0.01)

    def test_to_dict_includes_centrality(self):
        n = self._make_node()
        d = n.to_dict()
        assert "network_centrality" in d

    def test_to_summary(self):
        n = self._make_node()
        s = n.to_summary()
        assert isinstance(s, str)
        assert "Test Node" in s

    def test_is_key_node_default_false(self):
        n = self._make_node()
        assert n.is_key_node is False


class TestInfluenceEdge:
    def test_create(self):
        e = InfluenceEdge(
            source_node_id="src",
            target_node_id="tgt",
            relationship_type=InfluenceRelationshipType.INFLUENCES,
            weight=0.7,
        )
        assert e.edge_id != ""
        assert e.weight == 0.7

    def test_to_dict(self):
        e = InfluenceEdge(
            source_node_id="a",
            target_node_id="b",
            relationship_type=InfluenceRelationshipType.AMPLIFIES,
            weight=0.5,
        )
        d = e.to_dict()
        assert isinstance(d, dict)
        assert "edge_id" in d


class TestPropagationModel:
    def test_create(self):
        p = PropagationModel(
            narrative_id="n_001",
            origin_node_id="node_a",
            propagation_path=["node_a", "node_b", "node_c"],
            time_to_mainstream_hours=6.0,
            expected_reach_at_peak=500_000,
            bottleneck_nodes=["node_c"],
            accelerator_nodes=["node_a", "node_b"],
            suppressor_nodes=[],
        )
        assert p.narrative_id == "n_001"
        assert p.expected_reach_at_peak == 500_000

    def test_to_dict(self):
        p = PropagationModel(
            narrative_id="n_002",
            origin_node_id="origin",
            propagation_path=["origin", "relay"],
            time_to_mainstream_hours=12.0,
            expected_reach_at_peak=200_000,
            bottleneck_nodes=[],
            accelerator_nodes=["origin"],
            suppressor_nodes=[],
        )
        d = p.to_dict()
        assert isinstance(d, dict)


class TestInfluenceNetwork:
    def test_to_dict(self):
        n = InfluenceNetwork(
            nodes=[],
            edges=[],
            key_nodes=[],
            influence_rankings=[],
            propagation_models=[],
            total_nodes=0,
            total_edges=0,
            avg_influence_score=0.0,
        )
        d = n.to_dict()
        assert isinstance(d, dict)
        assert "network_id" in d


class TestInfluenceNetworkEngine:
    @pytest.fixture
    def engine(self):
        return InfluenceNetworkEngine()

    @pytest.mark.asyncio
    async def test_map_network(self, engine):
        network = await engine.map_network()
        assert isinstance(network, InfluenceNetwork)

    @pytest.mark.asyncio
    async def test_network_has_nodes(self, engine):
        network = await engine.map_network()
        assert network.total_nodes > 0
        assert len(network.nodes) == network.total_nodes

    @pytest.mark.asyncio
    async def test_network_has_edges(self, engine):
        network = await engine.map_network()
        assert network.total_edges >= 0

    @pytest.mark.asyncio
    async def test_key_nodes_identified(self, engine):
        network = await engine.map_network()
        assert isinstance(network.key_nodes, list)
        assert len(network.key_nodes) > 0

    @pytest.mark.asyncio
    async def test_influence_rankings(self, engine):
        network = await engine.map_network()
        assert isinstance(network.influence_rankings, list)

    @pytest.mark.asyncio
    async def test_propagation_models(self, engine):
        network = await engine.map_network()
        assert isinstance(network.propagation_models, list)

    @pytest.mark.asyncio
    async def test_avg_influence_positive(self, engine):
        network = await engine.map_network()
        assert network.avg_influence_score > 0

    @pytest.mark.asyncio
    async def test_get_node(self, engine):
        network = await engine.map_network()
        nid = network.nodes[0].node_id
        node = engine.get_node(nid)
        assert node is not None
        assert node.node_id == nid

    @pytest.mark.asyncio
    async def test_get_node_missing(self, engine):
        result = engine.get_node("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_key_nodes(self, engine):
        await engine.map_network()
        key = engine.get_key_nodes()
        assert isinstance(key, list)
        assert all(n.is_key_node for n in key)

    @pytest.mark.asyncio
    async def test_get_propagation_model(self, engine):
        await engine.map_network()
        model = await engine.get_propagation_model("test_narrative")
        assert isinstance(model, PropagationModel)
        assert model.narrative_id == "test_narrative"

    @pytest.mark.asyncio
    async def test_network_to_dict(self, engine):
        network = await engine.map_network()
        d = network.to_dict()
        assert isinstance(d, dict)
        assert "nodes" in d

    def test_singleton(self):
        a = get_influence_network_engine()
        b = get_influence_network_engine()
        assert a is b

    @pytest.mark.asyncio
    async def test_node_types_valid(self, engine):
        network = await engine.map_network()
        for node in network.nodes:
            assert node.node_type in InfluenceNodeType.__members__.values()

    @pytest.mark.asyncio
    async def test_history(self, engine):
        await engine.map_network()
        history = engine.get_history()
        assert isinstance(history, list)
