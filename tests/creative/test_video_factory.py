"""Tests for AI Video Factory (Package 8E)."""

from __future__ import annotations

import pytest

from sfc.creative.video.models import (
    AspectRatio,
    Storyboard,
    VideoAsset,
    VideoFormat,
    VideoGenerationReport,
    VideoProvider,
)
from sfc.creative.video.service import VideoFactoryService, get_video_factory_service


class TestVideoModels:
    def test_video_asset_defaults(self):
        asset = VideoAsset(video_format=VideoFormat.SHORT, title="Test")
        assert asset.asset_id
        assert asset.provider == VideoProvider.KLING
        assert asset.aspect_ratio == AspectRatio.VERTICAL

    def test_video_asset_to_dict(self):
        asset = VideoAsset(video_format=VideoFormat.REEL, title="Reel")
        d = asset.to_dict()
        assert d["video_format"] == "reel"
        assert d["title"] == "Reel"

    def test_video_asset_to_summary(self):
        asset = VideoAsset(video_format=VideoFormat.SHORT, title="Short Video", duration_seconds=60)
        summary = asset.to_summary()
        assert "60" in summary
        assert "Short Video" in summary

    def test_storyboard_defaults(self):
        sb = Storyboard()
        assert sb.storyboard_id
        assert sb.aspect_ratio == AspectRatio.VERTICAL


class TestVideoFactoryService:
    @pytest.mark.asyncio
    async def test_generate_video_returns_asset(self):
        service = VideoFactoryService()
        asset = await service.generate_video(
            title="Al Nassr Goal Reel",
            video_format=VideoFormat.REEL,
        )
        assert isinstance(asset, VideoAsset)
        assert asset.title == "Al Nassr Goal Reel"
        assert asset.duration_seconds > 0

    @pytest.mark.asyncio
    async def test_storyboard_generated(self):
        service = VideoFactoryService()
        asset = await service.generate_video(title="Test Video")
        assert asset.storyboard is not None
        assert asset.storyboard.total_scenes >= 3

    @pytest.mark.asyncio
    async def test_aspect_ratio_for_tiktok(self):
        service = VideoFactoryService()
        asset = await service.generate_video(
            title="TikTok Video",
            video_format=VideoFormat.TIKTOK,
            platform="tiktok",
        )
        assert asset.aspect_ratio == AspectRatio.VERTICAL

    @pytest.mark.asyncio
    async def test_generate_batch(self):
        service = VideoFactoryService()
        report = await service.generate_batch(
            titles=["Video A", "Video B"],
            video_format=VideoFormat.SHORT,
        )
        assert isinstance(report, VideoGenerationReport)
        assert report.total_generated == 2
        assert report.total_duration_seconds > 0
        assert len(report.providers_used) >= 1

    @pytest.mark.asyncio
    async def test_brand_score_populated(self):
        service = VideoFactoryService()
        asset = await service.generate_video(title="Brand Test")
        assert asset.brand_alignment_score > 0

    def test_singleton(self):
        s1 = get_video_factory_service()
        s2 = get_video_factory_service()
        assert s1 is s2
