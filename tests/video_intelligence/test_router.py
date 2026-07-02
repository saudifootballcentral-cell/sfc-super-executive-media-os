"""Tests for Video Production Router (Mode A/B/C decision)."""

from __future__ import annotations

import pytest

from sfc.video_intelligence.router.models import ProductionMode
from sfc.video_intelligence.router.service import VideoProductionRouter


def _clear_provider_env(monkeypatch):
    for var in ("KLING_API_KEY", "RUNWAYML_API_SECRET", "LUMA_API_KEY", "PIKA_API_KEY"):
        monkeypatch.delenv(var, raising=False)


class TestProductionRouter:
    @pytest.mark.asyncio
    async def test_footage_only_selects_real_footage(self, monkeypatch):
        _clear_provider_env(monkeypatch)
        router = VideoProductionRouter()
        d = await router.decide("topic", footage_sources=["clip.mp4"])
        assert d.mode == ProductionMode.REAL_FOOTAGE
        assert d.real_footage_available
        assert not d.ai_video_available

    @pytest.mark.asyncio
    async def test_ai_only_selects_ai_video(self, monkeypatch):
        _clear_provider_env(monkeypatch)
        monkeypatch.setenv("LUMA_API_KEY", "test-key")
        router = VideoProductionRouter()
        d = await router.decide("topic")
        assert d.mode == ProductionMode.AI_VIDEO
        assert d.ai_video_available

    @pytest.mark.asyncio
    async def test_both_available_selects_hybrid(self, monkeypatch):
        _clear_provider_env(monkeypatch)
        monkeypatch.setenv("KLING_API_KEY", "test-key")
        router = VideoProductionRouter()
        d = await router.decide("topic", footage_sources=["clip.mp4"])
        assert d.mode == ProductionMode.HYBRID
        assert d.real_footage_available
        assert d.ai_video_available

    @pytest.mark.asyncio
    async def test_nothing_available_falls_back_to_ai_low_confidence(self, monkeypatch):
        _clear_provider_env(monkeypatch)
        router = VideoProductionRouter()
        d = await router.decide("topic")
        assert d.mode == ProductionMode.AI_VIDEO
        assert d.confidence <= 0.5

    @pytest.mark.asyncio
    async def test_each_provider_env_enables_ai(self, monkeypatch):
        for var in ("KLING_API_KEY", "RUNWAYML_API_SECRET", "LUMA_API_KEY", "PIKA_API_KEY"):
            _clear_provider_env(monkeypatch)
            monkeypatch.setenv(var, "k")
            router = VideoProductionRouter()
            d = await router.decide("topic")
            assert d.ai_video_available, var

    @pytest.mark.asyncio
    async def test_decision_has_reason(self, monkeypatch):
        _clear_provider_env(monkeypatch)
        router = VideoProductionRouter()
        d = await router.decide("topic")
        assert d.reason
