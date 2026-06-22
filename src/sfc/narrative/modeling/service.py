"""Narrative Modeling Service — builds and maintains narrative profiles and maps."""

from __future__ import annotations

import logging
from typing import Any

from sfc.narrative.modeling.models import (
    NarrativeInfluenceModel,
    NarrativeMap,
    NarrativeProfile,
    NarrativeRelationship,
    NarrativeRelationshipType,
    NarrativeType,
)

logger = logging.getLogger("sfc.narrative.modeling")

_singleton: "NarrativeModelingService | None" = None

_NARRATIVE_RELATIONSHIP_PAIRS: list[tuple[int, int, str]] = [
    (0, 1, NarrativeRelationshipType.AMPLIFIES.value if hasattr(NarrativeRelationshipType, "AMPLIFIES") else "amplifies"),
    (2, 3, "amplifies"),
    (4, 5, "conflicts"),
    (6, 7, "amplifies"),
]


def get_narrative_modeling_service() -> "NarrativeModelingService":
    global _singleton
    if _singleton is None:
        _singleton = NarrativeModelingService()
    return _singleton


class NarrativeModelingService:
    """Builds and maintains detailed narrative profiles and relationship maps."""

    def __init__(self) -> None:
        self._gateway = None
        self._profiles: dict[str, NarrativeProfile] = {}
        self._relationships: list[NarrativeRelationship] = []
        self._history: list[NarrativeMap] = []
        self._max_history = 100

    @property
    def gateway(self):
        if self._gateway is None:
            from sfc.ai.model_gateway import get_ai_gateway
            self._gateway = get_ai_gateway()
        return self._gateway

    async def model_narratives(
        self,
        topics: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> list[NarrativeProfile]:
        """Build narrative profiles from topics and social context."""
        topics = topics or self._default_topics()
        profiles: list[NarrativeProfile] = []

        for topic in topics[:12]:
            profile = await self._build_profile(topic, context or {})
            self._profiles[profile.profile_id] = profile
            profiles.append(profile)

        self._build_relationships(profiles)
        return profiles

    async def build_narrative_map(
        self,
        profiles: list[NarrativeProfile] | None = None,
    ) -> NarrativeMap:
        """Build a complete narrative map with relationships and clusters."""
        if profiles is None:
            profiles = list(self._profiles.values())
        if not profiles:
            profiles = await self.model_narratives()

        dominant = max(profiles, key=lambda p: p.strength_score, default=None)
        clusters = self._detect_clusters(profiles)
        conflict_pairs = self._detect_conflicts(profiles)
        rels = [r for r in self._relationships]

        nmap = NarrativeMap(
            profiles=profiles,
            relationships=rels,
            dominant_narrative_id=dominant.profile_id if dominant else "",
            narrative_clusters=clusters,
            conflict_pairs=conflict_pairs,
            total_active=len(profiles),
        )

        if len(self._history) < self._max_history:
            self._history.append(nmap)

        return nmap

    def get_profile(self, profile_id: str) -> NarrativeProfile | None:
        return self._profiles.get(profile_id)

    def get_profiles_by_type(self, narrative_type: NarrativeType | None = None) -> list[NarrativeProfile]:
        profiles = list(self._profiles.values())
        if narrative_type is None:
            return profiles
        return [p for p in profiles if p.narrative_type == narrative_type]

    def get_history(self, limit: int = 10) -> list[dict[str, Any]]:
        return [m.to_dict() for m in self._history[-limit:]]

    async def _build_profile(self, topic: str, context: dict[str, Any]) -> NarrativeProfile:
        from sfc.data.fixtures.loader import get_fixture_loader
        loader = get_fixture_loader()
        topic_scores = loader.get_topic_scores()

        data = topic_scores.get(topic, {})
        if not data:
            for key, val in topic_scores.items():
                if any(w in key.lower() for w in topic.lower().split()):
                    data = val
                    break

        strength: float = float(data.get("score", 60.0))
        sentiment: float = float(data.get("score", 60.0)) * 0.95
        virality: float = float(data.get("score", 60.0)) * 0.9

        influence_model = NarrativeInfluenceModel(
            primary_drivers=["@SFCNews", "@SPL_EN"],
            amplifiers=["@AlHilalFanTV", "@TransferArabia"],
            suppressors=[],
            platform_weights={"x": 0.4, "instagram": 0.3, "tiktok": 0.2, "youtube": 0.1},
            influencer_impact=min(strength * 0.75, 70.0),
            media_impact=min(strength * 0.6, 60.0),
            organic_impact=min(strength * 0.55, 50.0),
        )

        ai_insights = await self._get_ai_profile_insights(topic)

        # Momentum uses velocity from fixture or a fixed moderate value
        momentum: float = float(data.get("velocity", 3.5)) * 10.0

        return NarrativeProfile(
            title=topic,
            narrative_type=self._classify_narrative_type(topic),
            description=ai_insights or f"Active narrative around {topic} in Saudi football.",
            entities=[topic],
            keywords=topic.lower().split()[:5],
            hashtags=[f"#{topic.replace(' ', '')}", "#SaudiFootball"],
            strength_score=round(strength, 1),
            momentum_score=round(min(momentum, 100.0), 1),
            sentiment_score=round(sentiment, 1),
            credibility_score=round(min(strength * 0.85, 90.0), 1),
            virality_potential=round(virality, 1),
            influence_model=influence_model,
            origin_platform="x",
            languages=["ar", "en"],
        )

    async def _get_ai_profile_insights(self, topic: str) -> str:
        try:
            from sfc.ai.models import ModelRequest
            req = ModelRequest(
                prompt=f"Describe Saudi football narrative: {topic}",
                task_type="narrative_modeling",
                max_tokens=100,
            )
            resp = await self.gateway.complete(req)
            return resp.content
        except Exception:
            return f"Narrative around {topic} is developing in Saudi football media."

    def _build_relationships(self, profiles: list[NarrativeProfile]) -> None:
        """Build deterministic relationships based on narrative type similarity."""
        for i, p1 in enumerate(profiles):
            for p2 in profiles[i + 1:]:
                if p1.narrative_type == p2.narrative_type:
                    rel_type = NarrativeRelationshipType.REINFORCES if hasattr(NarrativeRelationshipType, "REINFORCES") else list(NarrativeRelationshipType)[0]
                    strength = 0.6
                elif p1.sentiment_score > 50 and p2.sentiment_score < 40:
                    rel_type = NarrativeRelationshipType.CONFLICTS if hasattr(NarrativeRelationshipType, "CONFLICTS") else list(NarrativeRelationshipType)[1]
                    strength = 0.5
                else:
                    continue
                rel = NarrativeRelationship(
                    source_narrative_id=p1.profile_id,
                    target_narrative_id=p2.profile_id,
                    relationship_type=rel_type,
                    strength=strength,
                )
                self._relationships.append(rel)
                p1.related_narratives.append(p2.profile_id)

    def _detect_clusters(self, profiles: list[NarrativeProfile]) -> list[list[str]]:
        clusters: dict[NarrativeType, list[str]] = {}
        for p in profiles:
            clusters.setdefault(p.narrative_type, []).append(p.profile_id)
        return [ids for ids in clusters.values() if len(ids) > 1]

    def _detect_conflicts(self, profiles: list[NarrativeProfile]) -> list[tuple[str, str]]:
        conflicts = []
        for i, p1 in enumerate(profiles):
            for p2 in profiles[i + 1:]:
                if abs(p1.sentiment_score - p2.sentiment_score) > 60:
                    conflicts.append((p1.profile_id, p2.profile_id))
        return conflicts[:10]

    def _classify_narrative_type(self, topic: str) -> NarrativeType:
        t = topic.lower()
        if any(w in t for w in ["transfer", "signing", "deal", "contract"]):
            return NarrativeType.TRANSFER
        if any(w in t for w in ["national", "green falcons", "saudi team"]):
            return NarrativeType.NATIONAL_TEAM
        if any(w in t for w in ["club", "hilal", "nassr", "ittihad"]):
            return NarrativeType.CLUB
        if any(w in t for w in ["world cup", "tournament", "cup", "champion"]):
            return NarrativeType.TOURNAMENT
        if any(w in t for w in ["sponsor", "brand", "deal"]):
            return NarrativeType.SPONSOR
        if any(w in t for w in ["referee", "var", "decision"]):
            return NarrativeType.REFEREE
        if any(w in t for w in ["fan", "supporter", "ultras"]):
            return NarrativeType.FAN
        if any(w in t for w in ["media", "broadcast", "tv"]):
            return NarrativeType.MEDIA
        return NarrativeType.PLAYER

    def _default_topics(self) -> list[str]:
        return [
            "Al Hilal Champions League run",
            "Saudi Pro League quality debate",
            "Green Falcons World Cup qualification",
            "Foreign star player signing",
            "Saudi football academy development",
            "SPL broadcast rights expansion",
            "National team coach criticism",
            "Transfer window activity Saudi",
        ]
