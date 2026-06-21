"""Tests for Audience Intelligence Engine."""

from __future__ import annotations

import pytest

from sfc.social.audience.models import (
    AudienceProfile,
    AudienceReport,
    AudienceSegment,
    AudienceSegmentType,
)
from sfc.social.audience.service import AudienceIntelligenceService, get_audience_service


class TestAudienceSegmentType:
    def test_eight_types(self):
        assert len(AudienceSegmentType) == 8

    def test_type_values(self):
        values = {t.value for t in AudienceSegmentType}
        assert "core_fans" in values
        assert "youth_audience" in values
        assert "saudi_national_fans" in values
        assert "fantasy_players" in values


class TestAudienceSegment:
    def test_creation(self):
        seg = AudienceSegment(
            name="Core Fans",
            segment_type=AudienceSegmentType.CORE_FANS,
            size=500000,
            growth_rate=4.5,
        )
        assert seg.segment_id != ""
        assert seg.name == "Core Fans"
        assert seg.size == 500000

    def test_to_dict(self):
        seg = AudienceSegment(
            name="Youth",
            segment_type=AudienceSegmentType.YOUTH_AUDIENCE,
            size=1000000,
            growth_rate=20.0,
        )
        d = seg.to_dict()
        assert d["name"] == "Youth"
        assert d["segment_type"] == "youth_audience"
        assert d["size"] == 1000000

    def test_defaults(self):
        seg = AudienceSegment(name="Test", segment_type=AudienceSegmentType.CASUAL_VIEWERS)
        assert seg.size == 0
        assert seg.growth_rate == 0.0
        assert seg.peak_hours == []
        assert seg.preferred_platforms == []


class TestAudienceProfile:
    def test_defaults(self):
        p = AudienceProfile()
        assert p.profile_id != ""
        assert p.total_audience == 0
        assert p.peak_hour == 20

    def test_to_dict(self):
        p = AudienceProfile(total_audience=5000000, top_platform="x")
        d = p.to_dict()
        assert d["total_audience"] == 5000000
        assert d["top_platform"] == "x"


class TestAudienceReport:
    def test_defaults(self):
        r = AudienceReport()
        assert r.report_id != ""
        assert r.recommendations == []

    def test_to_dict(self):
        r = AudienceReport(ai_insights="Good growth trajectory.")
        d = r.to_dict()
        assert d["ai_insights"] == "Good growth trajectory."


class TestAudienceIntelligenceService:
    def test_singleton(self):
        assert get_audience_service() is get_audience_service()

    def test_init(self):
        service = AudienceIntelligenceService()
        assert service._profile is None

    @pytest.mark.asyncio
    async def test_analyze_returns_profile(self):
        service = AudienceIntelligenceService()
        profile = await service.analyze()
        assert isinstance(profile, AudienceProfile)
        assert profile.total_audience > 0

    @pytest.mark.asyncio
    async def test_analyze_all_segments(self):
        service = AudienceIntelligenceService()
        profile = await service.analyze()
        assert len(profile.segments) == len(AudienceSegmentType)

    @pytest.mark.asyncio
    async def test_analyze_specific_segments(self):
        service = AudienceIntelligenceService()
        profile = await service.analyze(
            segment_types=[AudienceSegmentType.CORE_FANS, AudienceSegmentType.YOUTH_AUDIENCE]
        )
        assert len(profile.segments) == 2

    @pytest.mark.asyncio
    async def test_analyze_sets_profile(self):
        service = AudienceIntelligenceService()
        await service.analyze()
        assert service._profile is not None

    @pytest.mark.asyncio
    async def test_get_segments_all(self):
        service = AudienceIntelligenceService()
        await service.analyze()
        segments = await service.get_segments()
        assert len(segments) > 0

    @pytest.mark.asyncio
    async def test_get_segments_filtered(self):
        service = AudienceIntelligenceService()
        await service.analyze()
        segments = await service.get_segments(segment_type=AudienceSegmentType.YOUTH_AUDIENCE)
        assert all(s.segment_type == AudienceSegmentType.YOUTH_AUDIENCE for s in segments)

    @pytest.mark.asyncio
    async def test_get_segments_triggers_analyze(self):
        service = AudienceIntelligenceService()
        segments = await service.get_segments()
        assert isinstance(segments, list)

    @pytest.mark.asyncio
    async def test_generate_report(self):
        service = AudienceIntelligenceService()
        report = await service.generate_report()
        assert isinstance(report, AudienceReport)

    @pytest.mark.asyncio
    async def test_report_has_segment_breakdown(self):
        service = AudienceIntelligenceService()
        report = await service.generate_report()
        assert len(report.segment_breakdown) > 0
        for item in report.segment_breakdown:
            assert "segment" in item
            assert "size" in item

    @pytest.mark.asyncio
    async def test_report_has_platform_breakdown(self):
        service = AudienceIntelligenceService()
        report = await service.generate_report()
        assert isinstance(report.platform_breakdown, dict)
        assert len(report.platform_breakdown) > 0

    @pytest.mark.asyncio
    async def test_report_has_engagement_patterns(self):
        service = AudienceIntelligenceService()
        report = await service.generate_report()
        patterns = report.engagement_patterns
        assert "peak_hour_utc" in patterns
        assert "peak_day" in patterns

    @pytest.mark.asyncio
    async def test_report_has_recommendations(self):
        service = AudienceIntelligenceService()
        report = await service.generate_report()
        assert isinstance(report.recommendations, list)

    @pytest.mark.asyncio
    async def test_report_ai_insights_not_empty(self):
        service = AudienceIntelligenceService()
        report = await service.generate_report()
        assert isinstance(report.ai_insights, str)
        assert len(report.ai_insights) > 0

    @pytest.mark.asyncio
    async def test_report_adds_to_history(self):
        service = AudienceIntelligenceService()
        await service.generate_report()
        history = service.get_history()
        assert len(history) >= 1
