"""Tests for Content Packaging Engine (Package 8E)."""

from __future__ import annotations

import pytest

from sfc.creative.packaging.models import (
    ContentPackage,
    PackagingReport,
    PackageType,
    PublishingMetadata,
)
from sfc.creative.packaging.service import ContentPackagingService, get_content_packaging_service


class TestPackagingModels:
    def test_publishing_metadata_defaults(self):
        meta = PublishingMetadata()
        assert meta.language == "arabic"
        assert meta.requires_approval is True

    def test_publishing_metadata_to_dict(self):
        meta = PublishingMetadata(platform="youtube", category="sports")
        d = meta.to_dict()
        assert d["platform"] == "youtube"
        assert d["language"] == "arabic"

    def test_content_package_to_dict(self):
        pkg = ContentPackage(package_type=PackageType.YOUTUBE_SHORT, title="Test")
        d = pkg.to_dict()
        assert d["package_type"] == "youtube_short"
        assert d["title"] == "Test"

    def test_content_package_to_summary(self):
        pkg = ContentPackage(
            package_type=PackageType.TIKTOK,
            title="Viral TikTok",
            ready_to_publish=True,
            quality_score=88.0,
        )
        summary = pkg.to_summary()
        assert "READY" in summary
        assert "Viral TikTok" in summary

    def test_packaging_report_to_dict(self):
        report = PackagingReport(total_packages=3, ready_to_publish=2)
        d = report.to_dict()
        assert d["total_packages"] == 3
        assert d["ready_to_publish"] == 2


class TestContentPackagingService:
    @pytest.mark.asyncio
    async def test_create_package_youtube_short(self):
        service = ContentPackagingService()
        pkg = await service.create_package(
            package_type=PackageType.YOUTUBE_SHORT,
            title="SPL Highlights",
            quality_score=85.0,
            governance_cleared=True,
        )
        assert isinstance(pkg, ContentPackage)
        assert pkg.package_type == PackageType.YOUTUBE_SHORT
        assert pkg.title == "SPL Highlights"

    @pytest.mark.asyncio
    async def test_ready_when_quality_and_governance_met(self):
        service = ContentPackagingService()
        pkg = await service.create_package(
            package_type=PackageType.INSTAGRAM,
            title="Ready Package",
            quality_score=75.0,
            governance_cleared=True,
        )
        assert pkg.ready_to_publish is True

    @pytest.mark.asyncio
    async def test_not_ready_without_governance(self):
        service = ContentPackagingService()
        pkg = await service.create_package(
            package_type=PackageType.TIKTOK,
            title="Uncleared Package",
            quality_score=90.0,
            governance_cleared=False,
        )
        assert pkg.ready_to_publish is False

    @pytest.mark.asyncio
    async def test_not_ready_low_quality(self):
        service = ContentPackagingService()
        pkg = await service.create_package(
            package_type=PackageType.PODCAST,
            title="Low Quality",
            quality_score=50.0,
            governance_cleared=True,
        )
        assert pkg.ready_to_publish is False

    @pytest.mark.asyncio
    async def test_hashtags_populated(self):
        service = ContentPackagingService()
        pkg = await service.create_package(
            package_type=PackageType.TIKTOK,
            title="Hashtag Test",
        )
        assert len(pkg.hashtags) > 0

    @pytest.mark.asyncio
    async def test_caption_generated(self):
        service = ContentPackagingService()
        pkg = await service.create_package(
            package_type=PackageType.INSTAGRAM,
            title="Caption Test",
        )
        assert pkg.caption != ""

    @pytest.mark.asyncio
    async def test_generate_packaging_report(self):
        service = ContentPackagingService()
        await service.create_package(PackageType.YOUTUBE_SHORT, "P1")
        await service.create_package(PackageType.TIKTOK, "P2")
        report = await service.generate_packaging_report()
        assert isinstance(report, PackagingReport)
        assert report.total_packages >= 2

    @pytest.mark.asyncio
    async def test_mark_governance_cleared(self):
        service = ContentPackagingService()
        pkg = await service.create_package(
            package_type=PackageType.INSTAGRAM,
            title="Clearance Test",
            quality_score=80.0,
            governance_cleared=False,
        )
        assert pkg.ready_to_publish is False
        result = service.mark_governance_cleared(pkg.package_id)
        assert result is True
        assert pkg.ready_to_publish is True

    def test_singleton(self):
        s1 = get_content_packaging_service()
        s2 = get_content_packaging_service()
        assert s1 is s2
