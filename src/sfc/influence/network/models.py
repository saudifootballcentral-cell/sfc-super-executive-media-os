"""Influence Network Engine models — nodes, edges, networks, and propagation."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class InfluenceNodeType(str, Enum):
    JOURNALIST = "journalist"
    CREATOR = "creator"
    MEDIA_OUTLET = "media_outlet"
    FORMER_PLAYER = "former_player"
    CLUB_ACCOUNT = "club_account"
    FEDERATION = "federation"
    SPONSOR = "sponsor"


class InfluenceRelationshipType(str, Enum):
    INFLUENCES = "influences"
    AMPLIFIES = "amplifies"
    SUPPORTS = "supports"
    OPPOSES = "opposes"
    ACCELERATES = "accelerates"
    SUPPRESSES = "suppresses"


class InfluenceNode(BaseModel):
    node_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    handle: str = ""
    node_type: InfluenceNodeType
    platforms: list[str] = Field(default_factory=list)
    followers: int = 0
    influence_score: float = 0.0        # 0-100
    reach_score: float = 0.0           # 0-100
    credibility_score: float = 0.0     # 0-100
    velocity_score: float = 0.0        # 0-100 trend in influence
    is_key_node: bool = False           # high-centrality node
    narrative_affinities: list[str] = Field(default_factory=list)  # narrative types they cover

    model_config = {"frozen": False}

    @property
    def network_centrality(self) -> float:
        return round(
            self.influence_score * 0.4 + self.reach_score * 0.3 + self.credibility_score * 0.3,
            1,
        )

    def to_dict(self) -> dict[str, Any]:
        return {**self.model_dump(mode="json"), "network_centrality": self.network_centrality}

    def to_summary(self) -> str:
        key = " [KEY NODE]" if self.is_key_node else ""
        return (
            f"{self.name} ({self.handle}) [{self.node_type.value}]{key} — "
            f"{self.followers:,} followers, centrality: {self.network_centrality:.1f}."
        )


class InfluenceEdge(BaseModel):
    edge_id: str = Field(default_factory=lambda: str(uuid4()))
    source_node_id: str
    target_node_id: str
    relationship_type: InfluenceRelationshipType
    weight: float = 0.5             # 0.0-1.0 relationship strength
    evidence: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class PropagationModel(BaseModel):
    narrative_id: str = ""
    origin_node_id: str = ""
    propagation_path: list[str] = Field(default_factory=list)    # node_ids in order
    time_to_mainstream_hours: float = 0.0
    expected_reach_at_peak: int = 0
    bottleneck_nodes: list[str] = Field(default_factory=list)    # nodes that slow spread
    accelerator_nodes: list[str] = Field(default_factory=list)   # nodes that speed spread
    suppressor_nodes: list[str] = Field(default_factory=list)    # nodes that block spread

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class InfluenceNetwork(BaseModel):
    network_id: str = Field(default_factory=lambda: str(uuid4()))
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    nodes: list[InfluenceNode] = Field(default_factory=list)
    edges: list[InfluenceEdge] = Field(default_factory=list)
    key_nodes: list[str] = Field(default_factory=list)           # high-centrality node_ids
    influence_rankings: list[dict[str, Any]] = Field(default_factory=list)
    propagation_models: list[PropagationModel] = Field(default_factory=list)
    total_nodes: int = 0
    total_edges: int = 0
    avg_influence_score: float = 0.0

    model_config = {"frozen": False}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
