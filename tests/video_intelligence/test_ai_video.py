"""Tests for AI Video Generation Service and provider chain (Mode B)."""

from __future__ import annotations

import pytest

from sfc.video_intelligence.ai_video.models import AIVideoResult, AIVideoStatus
from sfc.video_intelligence.ai_video.providers.base import AIVideoProvider
from sfc.video_intelligence.ai_video.service import AIVideoGenerationService
from sfc.video_intelligence.storyboard.models import Storyboard, StoryboardScene


def _scene(scene_id: str = "scene-1") -> StoryboardScene:
    return StoryboardScene(
        scene_id=scene_id,
        script_scene_id="sc-1",
        visual_prompt="Cinematic goal celebration",
        duration_seconds=5.0,
        aspect_ratio="9:16",
    )


class _FakeProvider(AIVideoProvider):
    """Configurable fake provider for chain tests."""

    def __init__(self, name: str, enabled: bool = True, succeed: bool = True,
                 raise_exc: bool = False) -> None:
        self._name = name
        self._enabled = enabled
        self._succeed = succeed
        self._raise = raise_exc
        self.calls = 0

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    async def generate(self, scene) -> AIVideoResult:
        self.calls += 1
        if self._raise:
            raise RuntimeError("provider exploded")
        if self._succeed:
            return AIVideoResult(
                provider=self._name,
                scene_id=scene.scene_id,
                status=AIVideoStatus.COMPLETED,
                local_path=f"/fake/{scene.scene_id}.mp4",  # already local → no download
                public_url=f"https://fake.example/{scene.scene_id}.mp4",
                duration_seconds=scene.duration_seconds,
            )
        return AIVideoResult(
            provider=self._name,
            scene_id=scene.scene_id,
            status=AIVideoStatus.FAILED,
            error_message="fake failure",
        )


def _clear_provider_env(monkeypatch):
    for var in ("KLING_API_KEY", "RUNWAYML_API_SECRET", "LUMA_API_KEY", "PIKA_API_KEY"):
        monkeypatch.delenv(var, raising=False)


class TestAIVideoService:
    @pytest.mark.asyncio
    async def test_no_providers_returns_skipped(self, monkeypatch):
        _clear_provider_env(monkeypatch)
        svc = AIVideoGenerationService()
        result = await svc.generate_scene(_scene())
        assert result.status == AIVideoStatus.SKIPPED
        assert not result.succeeded

    @pytest.mark.asyncio
    async def test_first_provider_success_stops_chain(self):
        svc = AIVideoGenerationService()
        p1 = _FakeProvider("p1", succeed=True)
        p2 = _FakeProvider("p2", succeed=True)
        svc._providers = [p1, p2]
        result = await svc.generate_scene(_scene())
        assert result.provider == "p1"
        assert result.succeeded
        assert p2.calls == 0

    @pytest.mark.asyncio
    async def test_fallback_to_next_provider_on_failure(self):
        svc = AIVideoGenerationService()
        p1 = _FakeProvider("p1", succeed=False)
        p2 = _FakeProvider("p2", succeed=True)
        svc._providers = [p1, p2]
        result = await svc.generate_scene(_scene())
        assert result.provider == "p2"
        assert result.succeeded
        assert p1.calls == 1

    @pytest.mark.asyncio
    async def test_fallback_on_provider_exception(self):
        svc = AIVideoGenerationService()
        p1 = _FakeProvider("p1", raise_exc=True)
        p2 = _FakeProvider("p2", succeed=True)
        svc._providers = [p1, p2]
        result = await svc.generate_scene(_scene())
        assert result.provider == "p2"
        assert result.succeeded

    @pytest.mark.asyncio
    async def test_all_providers_fail_returns_last_failure(self):
        svc = AIVideoGenerationService()
        svc._providers = [_FakeProvider("p1", succeed=False), _FakeProvider("p2", succeed=False)]
        result = await svc.generate_scene(_scene())
        assert result.status == AIVideoStatus.FAILED
        assert not result.succeeded

    @pytest.mark.asyncio
    async def test_disabled_providers_are_skipped(self):
        svc = AIVideoGenerationService()
        disabled = _FakeProvider("off", enabled=False, succeed=True)
        active = _FakeProvider("on", succeed=True)
        svc._providers = [disabled, active]
        result = await svc.generate_scene(_scene())
        assert result.provider == "on"
        assert disabled.calls == 0

    @pytest.mark.asyncio
    async def test_generate_video_returns_result_per_scene(self):
        svc = AIVideoGenerationService()
        svc._providers = [_FakeProvider("p1", succeed=True)]
        board = Storyboard(scenes=[_scene("s1"), _scene("s2"), _scene("s3")])
        results = await svc.generate_video(board)
        assert len(results) == 3
        assert {r.scene_id for r in results} == {"s1", "s2", "s3"}
        assert all(r.succeeded for r in results)

    @pytest.mark.asyncio
    async def test_persist_noop_when_already_local(self):
        svc = AIVideoGenerationService()
        result = AIVideoResult(
            provider="p", scene_id="s", status=AIVideoStatus.COMPLETED,
            local_path="/already/here.mp4", public_url="https://x/y.mp4",
        )
        persisted = await svc._persist(result)
        assert persisted.local_path == "/already/here.mp4"

    @pytest.mark.asyncio
    async def test_persist_noop_when_no_url(self):
        svc = AIVideoGenerationService()
        result = AIVideoResult(provider="p", scene_id="s", status=AIVideoStatus.COMPLETED)
        persisted = await svc._persist(result)
        assert persisted.local_path == ""

    @pytest.mark.asyncio
    async def test_persist_keeps_provider_url_on_download_failure(self):
        svc = AIVideoGenerationService()
        result = AIVideoResult(
            provider="p", scene_id="s", status=AIVideoStatus.COMPLETED,
            public_url="https://invalid.invalid/does-not-exist.mp4",
        )
        persisted = await svc._persist(result)
        assert persisted.public_url == "https://invalid.invalid/does-not-exist.mp4"
        assert persisted.local_path == ""


class TestRealProvidersDisabledByDefault:
    def test_all_providers_disabled_without_env(self, monkeypatch):
        _clear_provider_env(monkeypatch)
        from sfc.video_intelligence.ai_video.providers.kling import KlingVideoProvider
        from sfc.video_intelligence.ai_video.providers.luma import LumaVideoProvider
        from sfc.video_intelligence.ai_video.providers.pika import PikaVideoProvider
        from sfc.video_intelligence.ai_video.providers.runway import RunwayVideoProvider

        for cls in (KlingVideoProvider, RunwayVideoProvider, LumaVideoProvider, PikaVideoProvider):
            assert not cls().is_enabled, cls.__name__

    @pytest.mark.asyncio
    async def test_disabled_provider_returns_skipped(self, monkeypatch):
        _clear_provider_env(monkeypatch)
        from sfc.video_intelligence.ai_video.providers.kling import KlingVideoProvider

        result = await KlingVideoProvider().generate(_scene())
        assert result.status == AIVideoStatus.SKIPPED
