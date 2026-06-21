"""Tests for Narrative Modeling Engine."""

import pytest

from sfc.narrative.modeling.models import (
    NarrativeInfluenceModel,
    NarrativeMap,
    NarrativeProfile,
    NarrativeRelationship,
    NarrativeRelationshipType,
    NarrativeType,
)
from sfc.narrative.modeling.service import NarrativeModelingService, get_narrative_modeling_service


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

class TestNarrativeProfile:
    def _make_influence_model(self) -> NarrativeInfluenceModel:
        return NarrativeInfluenceModel(
            primary_drivers=["social"],
            amplifiers=["media"],
            suppressors=[],
            platform_weights={"x": 0.6},
            influencer_impact=0.7,
            media_impact=0.6,
            organic_impact=0.5,
        )

    def test_create(self):
        p = NarrativeProfile(
            title="Test Narrative",
            narrative_type=NarrativeType.PLAYER,
            description="A test",
            strength_score=70.0,
            momentum_score=60.0,
            sentiment_score=65.0,
            credibility_score=80.0,
            virality_potential=40.0,
            influence_model=self._make_influence_model(),
        )
        assert p.title == "Test Narrative"
        assert p.narrative_type == NarrativeType.PLAYER
        assert p.profile_id != ""

    def test_to_dict(self):
        p = NarrativeProfile(
            title="Dict Test",
            narrative_type=NarrativeType.CLUB,
            description="desc",
            strength_score=50.0,
            momentum_score=50.0,
            sentiment_score=50.0,
            credibility_score=50.0,
            virality_potential=50.0,
            influence_model=self._make_influence_model(),
        )
        d = p.to_dict()
        assert isinstance(d, dict)
        assert d["title"] == "Dict Test"
        assert "profile_id" in d

    def test_to_summary(self):
        p = NarrativeProfile(
            title="Summary Test",
            narrative_type=NarrativeType.TRANSFER,
            description="desc",
            strength_score=80.0,
            momentum_score=70.0,
            sentiment_score=75.0,
            credibility_score=85.0,
            virality_potential=55.0,
            influence_model=self._make_influence_model(),
        )
        s = p.to_summary()
        assert isinstance(s, str)
        assert "Summary Test" in s

    def test_defaults(self):
        p = NarrativeProfile(
            title="Default",
            narrative_type=NarrativeType.MEDIA,
            description="",
            strength_score=0.0,
            momentum_score=0.0,
            sentiment_score=50.0,
            credibility_score=50.0,
            virality_potential=0.0,
            influence_model=self._make_influence_model(),
        )
        assert p.entities == []
        assert p.keywords == []
        assert p.hashtags == []
        assert p.related_narratives == []
        assert p.competing_narratives == []


class TestNarrativeMap:
    def test_defaults(self):
        nm = NarrativeMap()
        assert nm.profiles == []
        assert nm.relationships == []

    def test_to_dict(self):
        nm = NarrativeMap(total_active=3)
        d = nm.to_dict()
        assert isinstance(d, dict)
        assert d["total_active"] == 3

    def test_with_profiles(self):
        influence = NarrativeInfluenceModel(
            primary_drivers=[],
            amplifiers=[],
            suppressors=[],
            platform_weights={},
            influencer_impact=0.5,
            media_impact=0.5,
            organic_impact=0.5,
        )
        p = NarrativeProfile(
            title="Profile",
            narrative_type=NarrativeType.FAN,
            description="",
            strength_score=50.0,
            momentum_score=50.0,
            sentiment_score=50.0,
            credibility_score=50.0,
            virality_potential=50.0,
            influence_model=influence,
        )
        nm = NarrativeMap(profiles=[p], total_active=1)
        assert len(nm.profiles) == 1


class TestNarrativeRelationship:
    def test_create(self):
        r = NarrativeRelationship(
            source_narrative_id="a",
            target_narrative_id="b",
            relationship_type=NarrativeRelationshipType.AMPLIFIES,
            strength=0.8,
        )
        assert r.relationship_id != ""
        assert r.strength == 0.8

    def test_to_dict(self):
        r = NarrativeRelationship(
            source_narrative_id="a",
            target_narrative_id="b",
            relationship_type=NarrativeRelationshipType.SUPPORTS,
            strength=0.5,
        )
        d = r.to_dict()
        assert d["relationship_type"] == NarrativeRelationshipType.SUPPORTS


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------

class TestNarrativeModelingService:
    @pytest.fixture
    def service(self):
        return NarrativeModelingService()

    @pytest.mark.asyncio
    async def test_model_narratives(self, service):
        profiles = await service.model_narratives()
        assert isinstance(profiles, list)
        assert len(profiles) > 0
        assert all(isinstance(p, NarrativeProfile) for p in profiles)

    @pytest.mark.asyncio
    async def test_build_narrative_map(self, service):
        nm = await service.build_narrative_map()
        assert isinstance(nm, NarrativeMap)
        assert nm.total_active >= 0

    @pytest.mark.asyncio
    async def test_map_profiles_list(self, service):
        nm = await service.build_narrative_map()
        assert isinstance(nm.profiles, list)

    @pytest.mark.asyncio
    async def test_map_relationships(self, service):
        nm = await service.build_narrative_map()
        assert isinstance(nm.relationships, list)

    @pytest.mark.asyncio
    async def test_get_profiles_by_type(self, service):
        await service.model_narratives()
        profiles = service.get_profiles_by_type()
        assert isinstance(profiles, list)

    @pytest.mark.asyncio
    async def test_get_profiles_by_type_filter(self, service):
        await service.model_narratives()
        profiles = service.get_profiles_by_type(NarrativeType.PLAYER)
        assert all(p.narrative_type == NarrativeType.PLAYER for p in profiles)

    @pytest.mark.asyncio
    async def test_get_profile(self, service):
        profiles = await service.model_narratives()
        pid = profiles[0].profile_id
        result = service.get_profile(pid)
        assert result is not None
        assert result.profile_id == pid

    @pytest.mark.asyncio
    async def test_get_profile_missing(self, service):
        result = service.get_profile("nonexistent")
        assert result is None

    def test_singleton(self):
        a = get_narrative_modeling_service()
        b = get_narrative_modeling_service()
        assert a is b

    @pytest.mark.asyncio
    async def test_map_to_dict(self, service):
        nm = await service.build_narrative_map()
        d = nm.to_dict()
        assert isinstance(d, dict)
        assert "profiles" in d

    @pytest.mark.asyncio
    async def test_profiles_have_required_fields(self, service):
        profiles = await service.model_narratives()
        for p in profiles:
            assert p.title != ""
            assert p.narrative_type in NarrativeType.__members__.values()
            assert 0 <= p.strength_score <= 100
            assert 0 <= p.sentiment_score <= 100
