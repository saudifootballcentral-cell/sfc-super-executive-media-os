"""Tests for AI Image Factory (Package 8E)."""

from __future__ import annotations

import pytest

from sfc.creative.image.models import (
    ImageAsset,
    ImageDimension,
    ImageFormat,
    ImageGenerationReport,
    ImageProvider,
    ImageVariant,
)
from sfc.creative.image.service import ImageFactoryService, get_image_factory_service


class TestImageModels:
    def test_image_variant_defaults(self):
        v = ImageVariant(label="v1")
        assert v.variant_id
        assert v.provider == ImageProvider.FLUX
        assert v.dimensions == ImageDimension.SQUARE

    def test_image_asset_to_dict(self):
        asset = ImageAsset(image_format=ImageFormat.SOCIAL_CARD, title="Test")
        d = asset.to_dict()
        assert d["image_format"] == "social_card"
        assert d["title"] == "Test"

    def test_image_asset_to_summary(self):
        asset = ImageAsset(image_format=ImageFormat.PLAYER_POSTER, title="Test Player")
        summary = asset.to_summary()
        assert "player_poster" in summary
        assert "Test Player" in summary

    def test_image_generation_report_serializable(self):
        report = ImageGenerationReport()
        d = report.to_dict()
        assert "assets" in d
        assert "total_generated" in d


class TestImageFactoryService:
    @pytest.mark.asyncio
    async def test_generate_image_returns_asset(self):
        service = ImageFactoryService()
        asset = await service.generate_image(
            title="Al Hilal Match Day",
            subject="Al Hilal",
            image_format=ImageFormat.MATCH_POSTER,
        )
        assert isinstance(asset, ImageAsset)
        assert asset.title == "Al Hilal Match Day"
        assert asset.image_format == ImageFormat.MATCH_POSTER
        assert len(asset.variants) >= 1

    @pytest.mark.asyncio
    async def test_variants_have_scores(self):
        service = ImageFactoryService()
        asset = await service.generate_image(title="Test", num_variants=2)
        for v in asset.variants:
            assert v.quality_score > 0
            assert v.brand_alignment_score > 0

    @pytest.mark.asyncio
    async def test_primary_variant_set(self):
        service = ImageFactoryService()
        asset = await service.generate_image(title="Test")
        assert asset.primary_variant_id != ""

    @pytest.mark.asyncio
    async def test_generate_batch(self):
        service = ImageFactoryService()
        report = await service.generate_batch(
            subjects=["Al Hilal", "Al Nassr"],
            image_format=ImageFormat.PLAYER_POSTER,
        )
        assert isinstance(report, ImageGenerationReport)
        assert report.total_generated == 2
        assert report.total_variants >= 2

    @pytest.mark.asyncio
    async def test_asset_tracked_in_service(self):
        service = ImageFactoryService()
        await service.generate_image(title="Tracked Asset")
        assert len(service.get_recent_assets()) >= 1

    def test_singleton(self):
        s1 = get_image_factory_service()
        s2 = get_image_factory_service()
        assert s1 is s2
