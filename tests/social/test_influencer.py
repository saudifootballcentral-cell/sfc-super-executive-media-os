"""Tests for Influencer Intelligence Engine."""

from __future__ import annotations

import pytest

from sfc.social.influencer.models import (
    InfluencerMetrics,
    InfluencerProfile,
    InfluencerReport,
    InfluencerType,
)
from sfc.social.influencer.service import InfluencerIntelligenceService, get_influencer_service


class TestInfluencerType:
    def test_six_types(self):
        assert len(InfluencerType) == 6
        values = {t.value for t in InfluencerType}
        assert "journalist" in values
        assert "creator" in values
        assert "analyst" in values
        assert "former_player" in values
        assert "club_account" in values
        assert "media_org" in values


class TestInfluencerMetrics:
    def test_defaults(self):
        m = InfluencerMetrics()
        assert m.influence_score == 0.0
        assert m.trust_score == 0.0
        assert m.engagement_rate == 0.0

    def test_composite_score_weighted(self):
        m = InfluencerMetrics(
            influence_score=100,
            trust_score=100,
            reach_score=100,
            velocity_score=100,
            authority_score=100,
        )
        # influence*0.3 + trust*0.2 + reach*0.2 + authority*0.3 = 100
        assert m.composite_score == pytest.approx(100.0, abs=0.1)

    def test_composite_score_zeros(self):
        m = InfluencerMetrics()
        assert m.composite_score == 0.0

    def test_composite_score_partial(self):
        m = InfluencerMetrics(influence_score=80, authority_score=60, trust_score=70, reach_score=50)
        # 80*0.3 + 70*0.2 + 50*0.2 + 60*0.3 = 24+14+10+18 = 66
        assert m.composite_score == pytest.approx(66.0, abs=0.1)


class TestInfluencerProfile:
    def test_creation(self):
        profile = InfluencerProfile(
            name="Saudi Sports Reporter",
            handle="@SSR",
            influencer_type=InfluencerType.JOURNALIST,
            platforms=["x"],
            followers=50000,
        )
        assert profile.influencer_id != ""
        assert profile.name == "Saudi Sports Reporter"
        assert profile.followers == 50000

    def test_default_language_arabic(self):
        profile = InfluencerProfile(
            name="Test",
            handle="@test",
            influencer_type=InfluencerType.CREATOR,
            platforms=["instagram"],
            followers=1000,
        )
        assert "ar" in profile.languages

    def test_to_dict(self):
        profile = InfluencerProfile(
            name="Al Hilal Fan",
            handle="@AlHilalFan",
            influencer_type=InfluencerType.CREATOR,
            platforms=["tiktok"],
            followers=250000,
        )
        d = profile.to_dict()
        assert d["name"] == "Al Hilal Fan"
        assert d["influencer_type"] == "creator"
        assert d["followers"] == 250000

    def test_to_summary(self):
        profile = InfluencerProfile(
            name="Analyst",
            handle="@analyst",
            influencer_type=InfluencerType.ANALYST,
            platforms=["x"],
            followers=30000,
        )
        s = profile.to_summary()
        assert "influencer_id" in s
        assert "name" in s
        assert "composite_score" in s


class TestInfluencerReport:
    def test_defaults(self):
        r = InfluencerReport()
        assert r.top_influencers == []
        assert r.total_tracked == 0

    def test_to_dict(self):
        r = InfluencerReport(total_tracked=5)
        d = r.to_dict()
        assert d["total_tracked"] == 5


class TestInfluencerIntelligenceService:
    def test_singleton(self):
        assert get_influencer_service() is get_influencer_service()

    def test_init(self):
        service = InfluencerIntelligenceService()
        assert service._influencers == {}

    @pytest.mark.asyncio
    async def test_scan_returns_profiles(self):
        service = InfluencerIntelligenceService()
        profiles = await service.scan()
        assert len(profiles) > 0
        assert all(isinstance(p, InfluencerProfile) for p in profiles)

    @pytest.mark.asyncio
    async def test_scan_populates_cache(self):
        service = InfluencerIntelligenceService()
        await service.scan()
        assert len(service._influencers) > 0

    @pytest.mark.asyncio
    async def test_get_top_influencers(self):
        service = InfluencerIntelligenceService()
        top = await service.get_top_influencers(limit=5)
        assert len(top) <= 5
        assert all(isinstance(p, InfluencerProfile) for p in top)

    @pytest.mark.asyncio
    async def test_get_top_influencers_sorted(self):
        service = InfluencerIntelligenceService()
        top = await service.get_top_influencers(limit=10)
        scores = [p.metrics.composite_score for p in top]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_get_top_by_type(self):
        service = InfluencerIntelligenceService()
        journalists = await service.get_top_influencers(
            limit=5, influencer_type=InfluencerType.JOURNALIST
        )
        assert all(p.influencer_type == InfluencerType.JOURNALIST for p in journalists)

    @pytest.mark.asyncio
    async def test_generate_report(self):
        service = InfluencerIntelligenceService()
        report = await service.generate_report()
        assert isinstance(report, InfluencerReport)
        assert report.total_tracked > 0

    @pytest.mark.asyncio
    async def test_report_has_rankings(self):
        service = InfluencerIntelligenceService()
        report = await service.generate_report()
        assert isinstance(report.influence_rankings, list)
        assert len(report.influence_rankings) > 0

    @pytest.mark.asyncio
    async def test_report_has_media_map(self):
        service = InfluencerIntelligenceService()
        report = await service.generate_report()
        assert isinstance(report.media_map, dict)
        # Should have entries for various types
        all_types = list(report.media_map.keys())
        assert len(all_types) > 0

    def test_get_influencer_none(self):
        service = InfluencerIntelligenceService()
        assert service.get_influencer("nonexistent") is None

    @pytest.mark.asyncio
    async def test_get_influencer_after_scan(self):
        service = InfluencerIntelligenceService()
        await service.scan()
        first_id = list(service._influencers.keys())[0]
        profile = service.get_influencer(first_id)
        assert profile is not None

    @pytest.mark.asyncio
    async def test_get_history(self):
        service = InfluencerIntelligenceService()
        await service.generate_report()
        history = service.get_history()
        assert isinstance(history, list)
