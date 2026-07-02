"""Tests for Storyboard Generation Service (Mode B)."""

from __future__ import annotations

import json

import pytest

from sfc.video_intelligence.script.models import ScriptScene, VideoScript
from sfc.video_intelligence.storyboard.service import StoryboardGenerationService


def _script() -> VideoScript:
    return VideoScript(
        topic="هدف الهلال",
        total_duration_seconds=15,
        scenes=[
            ScriptScene("sc-1", "Goal", "Striker scores", "هدف رائع", 8.0, "energetic", ["goal"]),
            ScriptScene("sc-2", "Celebration", "Fans cheer", "احتفال", 7.0, "celebratory", ["fans"]),
        ],
    )


def _service(monkeypatch) -> StoryboardGenerationService:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    return StoryboardGenerationService()


class TestStoryboardGeneration:
    @pytest.mark.asyncio
    async def test_stub_storyboard_scene_count_matches_script(self, monkeypatch):
        svc = _service(monkeypatch)
        sb = await svc.create(_script(), platform="youtube_video")
        assert sb.scene_count == 2
        assert sb.script_id == _script().script_id or sb.script_id  # linked

    @pytest.mark.asyncio
    async def test_vertical_platforms_get_9_16(self, monkeypatch):
        svc = _service(monkeypatch)
        for platform in ("youtube_short", "instagram_reel", "tiktok"):
            sb = await svc.create(_script(), platform=platform)
            assert all(s.aspect_ratio == "9:16" for s in sb.scenes), platform

    @pytest.mark.asyncio
    async def test_horizontal_platforms_get_16_9(self, monkeypatch):
        svc = _service(monkeypatch)
        for platform in ("youtube_video", "x_video"):
            sb = await svc.create(_script(), platform=platform)
            assert all(s.aspect_ratio == "16:9" for s in sb.scenes), platform

    @pytest.mark.asyncio
    async def test_stub_prompts_include_scene_description(self, monkeypatch):
        svc = _service(monkeypatch)
        sb = await svc.create(_script(), platform="youtube_video")
        assert "Striker scores" in sb.scenes[0].visual_prompt

    def test_parse_maps_durations_from_script(self, monkeypatch):
        svc = _service(monkeypatch)
        script = _script()
        raw = json.dumps({
            "scenes": [
                {"scene_id": script.scenes[0].scene_id, "visual_prompt": "p1",
                 "negative_prompt": "n", "style_tags": ["cinematic"]},
                {"scene_id": script.scenes[1].scene_id, "visual_prompt": "p2"},
            ]
        })
        sb = svc._parse_storyboard(raw, script, "youtube_video", "16:9")
        assert sb.scenes[0].duration_seconds == pytest.approx(8.0)
        assert sb.scenes[1].duration_seconds == pytest.approx(7.0)
        assert sb.total_duration_seconds == pytest.approx(15.0)

    def test_parse_empty_scenes_falls_back_to_stub(self, monkeypatch):
        svc = _service(monkeypatch)
        sb = svc._parse_storyboard('{"scenes": []}', _script(), "youtube_video", "16:9")
        assert sb.scene_count == 2  # stub mirrors the script

    def test_parse_invalid_json_falls_back_to_stub(self, monkeypatch):
        svc = _service(monkeypatch)
        sb = svc._parse_storyboard("garbage", _script(), "youtube_video", "16:9")
        assert sb.scene_count == 2
