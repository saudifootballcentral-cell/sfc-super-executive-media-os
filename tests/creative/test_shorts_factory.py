"""Tests for AI Shorts Factory (Package 8E)."""

from __future__ import annotations

import pytest

from sfc.creative.shorts.models import (
    ShortsPlatform,
    ShortsPackage,
    ShortsScript,
    ShortsScene,
)
from sfc.creative.shorts.service import ShortsFactoryService, get_shorts_factory_service


class TestShortsModels:
    def test_shorts_script_defaults(self):
        script = ShortsScript()
        assert script.script_id
        assert script.word_count == 0

    def test_shorts_scene_defaults(self):
        scene = ShortsScene()
        assert scene.scene_number == 1
        assert scene.duration_seconds == 3.0

    def test_shorts_package_to_dict(self):
        pkg = ShortsPackage(
            title="Test", platform=ShortsPlatform.TIKTOK
        )
        d = pkg.to_dict()
        assert d["platform"] == "tiktok"

    def test_shorts_package_to_summary(self):
        pkg = ShortsPackage(
            title="Goal Reel",
            platform=ShortsPlatform.YOUTUBE_SHORTS,
            duration_seconds=45,
        )
        summary = pkg.to_summary()
        assert "Goal Reel" in summary
        assert "45" in summary


class TestShortsFactoryService:
    @pytest.mark.asyncio
    async def test_generate_youtube_shorts(self):
        service = ShortsFactoryService()
        pkg = await service.generate_shorts_package(
            title="Al Hilal Win!",
            platform=ShortsPlatform.YOUTUBE_SHORTS,
        )
        assert isinstance(pkg, ShortsPackage)
        assert pkg.platform == ShortsPlatform.YOUTUBE_SHORTS

    @pytest.mark.asyncio
    async def test_script_non_empty(self):
        service = ShortsFactoryService()
        pkg = await service.generate_shorts_package(title="Test Shorts")
        assert pkg.script.hook != ""
        assert pkg.script.call_to_action != ""

    @pytest.mark.asyncio
    async def test_hashtags_populated(self):
        service = ShortsFactoryService()
        pkg = await service.generate_shorts_package(
            title="Viral Clip", platform=ShortsPlatform.TIKTOK
        )
        assert len(pkg.hashtags) > 0
        assert all(h.startswith("#") for h in pkg.hashtags)

    @pytest.mark.asyncio
    async def test_storyboard_generated(self):
        service = ShortsFactoryService()
        pkg = await service.generate_shorts_package(title="Storyboard Test")
        assert len(pkg.storyboard) >= 3

    @pytest.mark.asyncio
    async def test_generate_multi_platform(self):
        service = ShortsFactoryService()
        packages = await service.generate_multi_platform(
            title="SPL Highlights", narrative="SPL matchday"
        )
        assert len(packages) == 3
        platforms = {p.platform for p in packages}
        assert platforms == set(ShortsPlatform)

    @pytest.mark.asyncio
    async def test_duration_set(self):
        service = ShortsFactoryService()
        pkg = await service.generate_shorts_package(title="Duration Test")
        assert pkg.duration_seconds > 0

    def test_singleton(self):
        s1 = get_shorts_factory_service()
        s2 = get_shorts_factory_service()
        assert s1 is s2
