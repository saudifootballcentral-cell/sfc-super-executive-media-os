"""Tests for AI Audio Factory (Package 8E)."""

from __future__ import annotations

import pytest

from sfc.creative.audio.models import (
    AudioAsset,
    AudioPackage,
    AudioProvider,
    AudioType,
    VoiceLanguage,
)
from sfc.creative.audio.service import AudioFactoryService, get_audio_factory_service


class TestAudioModels:
    def test_audio_asset_defaults(self):
        asset = AudioAsset(audio_type=AudioType.NEWS_BRIEF)
        assert asset.asset_id
        assert asset.provider == AudioProvider.ELEVENLABS
        assert asset.language == VoiceLanguage.ARABIC

    def test_audio_asset_to_dict(self):
        asset = AudioAsset(audio_type=AudioType.NARRATION, title="Test")
        d = asset.to_dict()
        assert d["audio_type"] == "narration"

    def test_audio_asset_to_summary(self):
        asset = AudioAsset(
            audio_type=AudioType.NEWS_BRIEF, title="Daily Brief", duration_seconds=30
        )
        summary = asset.to_summary()
        assert "news_brief" in summary
        assert "30" in summary

    def test_audio_package_fields(self):
        pkg = AudioPackage(title="Package", language=VoiceLanguage.ARABIC, total_assets=3)
        assert pkg.title == "Package"
        assert pkg.total_assets == 3

    def test_audio_package_to_summary(self):
        pkg = AudioPackage(title="SFC Daily", total_assets=4, total_duration_seconds=120)
        summary = pkg.to_summary()
        assert "SFC Daily" in summary
        assert "4" in summary


class TestAudioFactoryService:
    @pytest.mark.asyncio
    async def test_generate_audio_news_brief(self):
        service = AudioFactoryService()
        asset = await service.generate_audio(
            title="SPL Round 10 Brief",
            audio_type=AudioType.NEWS_BRIEF,
            language=VoiceLanguage.ARABIC,
        )
        assert isinstance(asset, AudioAsset)
        assert asset.audio_type == AudioType.NEWS_BRIEF
        assert asset.duration_seconds > 0

    @pytest.mark.asyncio
    async def test_word_count_populated(self):
        service = AudioFactoryService()
        asset = await service.generate_audio(title="Test", audio_type=AudioType.NARRATION)
        assert asset.word_count > 0

    @pytest.mark.asyncio
    async def test_arabic_voice_id(self):
        service = AudioFactoryService()
        asset = await service.generate_audio(
            title="Arabic Test", language=VoiceLanguage.ARABIC
        )
        assert "arabic" in asset.voice_id

    @pytest.mark.asyncio
    async def test_generate_package(self):
        service = AudioFactoryService()
        package = await service.generate_package(
            title="SFC Weekly",
            narratives=["Transfer rumour", "Match recap"],
        )
        assert isinstance(package, AudioPackage)
        assert package.total_assets >= 1
        assert package.total_duration_seconds > 0

    @pytest.mark.asyncio
    async def test_quality_score_set(self):
        service = AudioFactoryService()
        asset = await service.generate_audio(title="Quality Test")
        assert asset.quality_score > 0

    def test_singleton(self):
        s1 = get_audio_factory_service()
        s2 = get_audio_factory_service()
        assert s1 is s2
