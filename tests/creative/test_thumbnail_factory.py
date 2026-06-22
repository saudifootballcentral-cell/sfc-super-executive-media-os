"""Tests for AI Thumbnail Factory (Package 8E)."""

from __future__ import annotations

import pytest

from sfc.creative.thumbnail.models import (
    CTRPrediction,
    ThumbnailAsset,
    ThumbnailVariant,
    ThumbnailVariantLabel,
)
from sfc.creative.thumbnail.service import ThumbnailFactoryService, get_thumbnail_factory_service


class TestThumbnailModels:
    def test_ctr_prediction_defaults(self):
        pred = CTRPrediction()
        assert pred.ctr_score == 0.0
        assert pred.emotional_hook == ""

    def test_thumbnail_variant_to_dict(self):
        v = ThumbnailVariant(label=ThumbnailVariantLabel.A)
        d = v.to_dict()
        assert d["label"] == "A"

    def test_thumbnail_asset_to_summary(self):
        asset = ThumbnailAsset(content_title="Match Highlights")
        summary = asset.to_summary()
        assert "Match Highlights" in summary

    def test_thumbnail_asset_to_dict(self):
        asset = ThumbnailAsset(content_title="Test")
        d = asset.to_dict()
        assert "content_title" in d
        assert "variants" in d


class TestThumbnailFactoryService:
    @pytest.mark.asyncio
    async def test_generates_four_variants(self):
        service = ThumbnailFactoryService()
        asset = await service.generate_thumbnails(
            content_title="SFC Match Day Highlights"
        )
        assert isinstance(asset, ThumbnailAsset)
        assert len(asset.variants) == 4

    @pytest.mark.asyncio
    async def test_all_variant_labels_present(self):
        service = ThumbnailFactoryService()
        asset = await service.generate_thumbnails(content_title="Test")
        labels = {v.label for v in asset.variants}
        assert labels == set(ThumbnailVariantLabel)

    @pytest.mark.asyncio
    async def test_recommended_variant_set(self):
        service = ThumbnailFactoryService()
        asset = await service.generate_thumbnails(content_title="Goal!")
        assert asset.recommended_variant is not None

    @pytest.mark.asyncio
    async def test_best_ctr_score_positive(self):
        service = ThumbnailFactoryService()
        asset = await service.generate_thumbnails(content_title="Match")
        assert asset.best_ctr_score > 0

    @pytest.mark.asyncio
    async def test_ctr_predictions_vary(self):
        service = ThumbnailFactoryService()
        asset = await service.generate_thumbnails(content_title="Variants Test")
        scores = [v.ctr_prediction.ctr_score for v in asset.variants]
        assert not all(s == scores[0] for s in scores)

    @pytest.mark.asyncio
    async def test_ai_recommendation_non_empty(self):
        service = ThumbnailFactoryService()
        asset = await service.generate_thumbnails(content_title="Recommend Me")
        assert asset.ai_recommendation != ""

    def test_singleton(self):
        s1 = get_thumbnail_factory_service()
        s2 = get_thumbnail_factory_service()
        assert s1 is s2
