"""Influence Network Engine — maps information flow across Saudi football media."""

from __future__ import annotations

import logging
import random
from typing import Any

from sfc.influence.network.models import (
    InfluenceEdge,
    InfluenceNetwork,
    InfluenceNode,
    InfluenceNodeType,
    InfluenceRelationshipType,
    PropagationModel,
)

logger = logging.getLogger("sfc.influence.network")

_singleton: "InfluenceNetworkEngine | None" = None


def get_influence_network_engine() -> "InfluenceNetworkEngine":
    global _singleton
    if _singleton is None:
        _singleton = InfluenceNetworkEngine()
    return _singleton


class InfluenceNetworkEngine:
    """Maps information flow and influence pathways in Saudi football media."""

    def __init__(self) -> None:
        self._gateway = None
        self._nodes: dict[str, InfluenceNode] = {}
        self._edges: list[InfluenceEdge] = []
        self._networks: list[InfluenceNetwork] = []
        self._max_history = 100

    @property
    def gateway(self):
        if self._gateway is None:
            from sfc.ai.model_gateway import get_ai_gateway
            self._gateway = get_ai_gateway()
        return self._gateway

    async def map_network(
        self,
        context: dict[str, Any] | None = None,
    ) -> InfluenceNetwork:
        """Build the full influence network for Saudi football."""
        nodes = self._build_default_nodes()
        for node in nodes:
            self._nodes[node.node_id] = node

        edges = self._build_edges(nodes)
        self._edges.extend(edges)

        key_nodes = [n.node_id for n in sorted(nodes, key=lambda n: n.network_centrality, reverse=True)[:5]]
        for nid in key_nodes:
            self._nodes[nid].is_key_node = True

        rankings = [
            {"rank": i + 1, "node_id": n.node_id, "name": n.name, "centrality": n.network_centrality}
            for i, n in enumerate(sorted(nodes, key=lambda n: n.network_centrality, reverse=True)[:10])
        ]

        propagation_models = await self._build_propagation_models(nodes[:3])
        avg_influence = sum(n.influence_score for n in nodes) / max(len(nodes), 1)

        network = InfluenceNetwork(
            nodes=nodes,
            edges=edges,
            key_nodes=key_nodes,
            influence_rankings=rankings,
            propagation_models=propagation_models,
            total_nodes=len(nodes),
            total_edges=len(edges),
            avg_influence_score=round(avg_influence, 1),
        )

        if len(self._networks) < self._max_history:
            self._networks.append(network)

        return network

    async def get_propagation_model(
        self,
        narrative_id: str,
        origin_node_id: str | None = None,
    ) -> PropagationModel:
        """Model how a narrative propagates through the influence network."""
        if not self._nodes:
            await self.map_network()

        nodes = list(self._nodes.values())
        origin = origin_node_id or (nodes[0].node_id if nodes else "")
        path = [n.node_id for n in sorted(nodes, key=lambda n: n.network_centrality, reverse=True)[:5]]

        return PropagationModel(
            narrative_id=narrative_id,
            origin_node_id=origin,
            propagation_path=path,
            time_to_mainstream_hours=random.uniform(2, 18),
            expected_reach_at_peak=random.randint(50000, 2000000),
            bottleneck_nodes=path[-1:] if path else [],
            accelerator_nodes=path[:2] if path else [],
            suppressor_nodes=[],
        )

    def get_node(self, node_id: str) -> InfluenceNode | None:
        return self._nodes.get(node_id)

    def get_key_nodes(self) -> list[InfluenceNode]:
        return [n for n in self._nodes.values() if n.is_key_node]

    def get_history(self, limit: int = 10) -> list[dict[str, Any]]:
        return [n.to_dict() for n in self._networks[-limit:]]

    def _build_default_nodes(self) -> list[InfluenceNode]:
        node_data = [
            ("Saudi Football Daily", "@SFD_News", InfluenceNodeType.JOURNALIST, 450000, 85, 80, 88),
            ("SPL Insider", "@SPL_Insider", InfluenceNodeType.JOURNALIST, 380000, 78, 75, 82),
            ("Al Hilal Fan TV", "@AlHilalFanTV", InfluenceNodeType.CREATOR, 620000, 82, 88, 70),
            ("Arabic Football Analysis", "@AFA", InfluenceNodeType.CREATOR, 290000, 70, 72, 75),
            ("خالد الغامدي", "@khaled_ghamdi", InfluenceNodeType.FORMER_PLAYER, 890000, 90, 85, 92),
            ("محمد العويس", "@m_alowais", InfluenceNodeType.FORMER_PLAYER, 1200000, 92, 88, 94),
            ("Al Nassr Official", "@AlNassrFC", InfluenceNodeType.CLUB_ACCOUNT, 5500000, 95, 96, 85),
            ("Al Hilal Official", "@Alhilal_EN", InfluenceNodeType.CLUB_ACCOUNT, 7200000, 97, 98, 88),
            ("Saudi Football Federation", "@saff", InfluenceNodeType.FEDERATION, 2100000, 88, 90, 95),
            ("SPL Media", "@SPL_EN", InfluenceNodeType.MEDIA_OUTLET, 1800000, 85, 86, 90),
            ("Transfer Arabia", "@TransferArabia", InfluenceNodeType.CREATOR, 560000, 80, 82, 72),
            ("Main Sponsor Media", "@SponsorMedia", InfluenceNodeType.SPONSOR, 320000, 72, 70, 60),
        ]

        nodes = []
        for name, handle, ntype, followers, inf, reach, cred in node_data:
            node = InfluenceNode(
                name=name,
                handle=handle,
                node_type=ntype,
                platforms=["x", "instagram"],
                followers=followers,
                influence_score=round(inf * random.uniform(0.9, 1.1), 1),
                reach_score=round(reach * random.uniform(0.9, 1.1), 1),
                credibility_score=round(cred * random.uniform(0.9, 1.1), 1),
                velocity_score=round(random.uniform(50, 85), 1),
                narrative_affinities=["player", "transfer", "national_team"],
            )
            nodes.append(node)

        return nodes

    def _build_edges(self, nodes: list[InfluenceNode]) -> list[InfluenceEdge]:
        edges = []
        rel_types = list(InfluenceRelationshipType)

        for i, source in enumerate(nodes):
            targets = sorted(
                [n for n in nodes if n != source],
                key=lambda n: n.network_centrality,
                reverse=True,
            )[:3]

            for target in targets:
                if random.random() > 0.4:
                    edges.append(InfluenceEdge(
                        source_node_id=source.node_id,
                        target_node_id=target.node_id,
                        relationship_type=random.choice(rel_types),
                        weight=round(random.uniform(0.3, 0.9), 2),
                    ))

        return edges

    async def _build_propagation_models(
        self, nodes: list[InfluenceNode]
    ) -> list[PropagationModel]:
        models = []
        for node in nodes:
            models.append(PropagationModel(
                narrative_id=f"narrative_{node.node_id[:8]}",
                origin_node_id=node.node_id,
                propagation_path=[n.node_id for n in nodes],
                time_to_mainstream_hours=round(24 / max(node.influence_score / 20, 1), 1),
                expected_reach_at_peak=int(node.followers * random.uniform(2, 8)),
                bottleneck_nodes=[],
                accelerator_nodes=[node.node_id],
                suppressor_nodes=[],
            ))
        return models
