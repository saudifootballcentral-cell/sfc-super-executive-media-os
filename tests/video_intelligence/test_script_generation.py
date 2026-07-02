"""Tests for Script Generation Service (Mode B)."""

from __future__ import annotations

import json

import pytest

from sfc.video_intelligence.script.models import ScriptScene, VideoScript
from sfc.video_intelligence.script.service import ScriptGenerationService


def _service(monkeypatch, api_key: str = "") -> ScriptGenerationService:
    if api_key:
        monkeypatch.setenv("ANTHROPIC_API_KEY", api_key)
    else:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    return ScriptGenerationService()


class TestScriptGeneration:
    @pytest.mark.asyncio
    async def test_stub_script_when_no_api_key(self, monkeypatch):
        svc = _service(monkeypatch)
        script = await svc.generate("هدف الهلال", duration_secs=30, num_scenes=3)
        assert script.generated_by == "stub"
        assert script.scene_count == 3
        assert script.total_duration_seconds == 30
        assert script.language == "ar"

    @pytest.mark.asyncio
    async def test_stub_scene_durations_sum_to_total(self, monkeypatch):
        svc = _service(monkeypatch)
        script = await svc.generate("test", duration_secs=60, num_scenes=4)
        assert sum(s.duration_seconds for s in script.scenes) == pytest.approx(60)

    @pytest.mark.asyncio
    async def test_default_scene_count_from_duration(self, monkeypatch):
        svc = _service(monkeypatch)
        script = await svc.generate("test", duration_secs=60)
        assert script.scene_count == 6  # 60s / 10s per scene

    def test_parse_valid_json(self, monkeypatch):
        svc = _service(monkeypatch)
        raw = json.dumps({
            "topic": "goal",
            "style": "sports_highlight",
            "scenes": [
                {"title": "t1", "description": "d1", "narration": "n1",
                 "duration_seconds": 5, "visual_style": "energetic", "keywords": ["a"]},
                {"title": "t2", "description": "d2", "narration": "n2",
                 "duration_seconds": 7, "visual_style": "dramatic", "keywords": []},
            ],
        })
        script = svc._parse_script(raw, "goal", 12, "sports_highlight", "ar")
        assert script.scene_count == 2
        assert script.total_duration_seconds == pytest.approx(12)
        assert script.scenes[0].visual_style == "energetic"

    def test_parse_json_wrapped_in_code_fences(self, monkeypatch):
        svc = _service(monkeypatch)
        raw = '```json\n{"topic": "x", "scenes": [{"title": "t", "narration": "n", "duration_seconds": 5}]}\n```'
        script = svc._parse_script(raw, "x", 5, "sports_highlight", "ar")
        assert script.scene_count == 1

    def test_parse_invalid_json_falls_back_to_stub(self, monkeypatch):
        svc = _service(monkeypatch)
        script = svc._parse_script("not json at all", "topic", 30, "sports_highlight", "ar")
        assert script.generated_by == "stub"
        assert script.scene_count == 3

    def test_parse_empty_scenes_falls_back_to_stub(self, monkeypatch):
        svc = _service(monkeypatch)
        script = svc._parse_script('{"topic": "x", "scenes": []}', "x", 30, "sports_highlight", "ar")
        assert script.generated_by == "stub"
        assert script.scene_count == 3

    def test_total_narration_joins_scenes(self):
        script = VideoScript(
            topic="t",
            scenes=[
                ScriptScene("1", "a", "d", "أول", 5, "calm"),
                ScriptScene("2", "b", "d", "ثاني", 5, "calm"),
            ],
        )
        assert script.total_narration == "أول ثاني"
