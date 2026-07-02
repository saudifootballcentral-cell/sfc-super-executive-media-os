"""Tests for orchestrator Mode B (AI video), Mode C (hybrid), and auto routing."""

from __future__ import annotations

import pytest

from sfc.video_intelligence.ai_video.models import AIVideoResult, AIVideoStatus
from sfc.video_intelligence.orchestrator import VideoIntelligenceOrchestrator
from sfc.video_intelligence.script.models import ScriptScene, VideoScript
from sfc.video_intelligence.storyboard.models import Storyboard, StoryboardScene


def _clear_env(monkeypatch):
    for var in (
        "KLING_API_KEY", "RUNWAYML_API_SECRET", "LUMA_API_KEY", "PIKA_API_KEY",
        "ANTHROPIC_API_KEY",
    ):
        monkeypatch.delenv(var, raising=False)


def _script_and_storyboard():
    script = VideoScript(
        topic="t",
        total_duration_seconds=10,
        scenes=[
            ScriptScene("sc-1", "A", "desc a", "narr a", 5.0, "energetic"),
            ScriptScene("sc-2", "B", "desc b", "narr b", 5.0, "dramatic"),
        ],
    )
    board = Storyboard(
        script_id=script.script_id,
        platform="youtube_short",
        scenes=[
            StoryboardScene("sb-1", "sc-1", "prompt a", duration_seconds=5.0, aspect_ratio="9:16"),
            StoryboardScene("sb-2", "sc-2", "prompt b", duration_seconds=5.0, aspect_ratio="9:16"),
        ],
    )
    return script, board


class TestModeB:
    @pytest.mark.asyncio
    async def test_process_ai_video_stub_end_to_end(self, monkeypatch):
        _clear_env(monkeypatch)
        orch = VideoIntelligenceOrchestrator()
        result = await orch.process_ai_video(
            topic="هدف الهلال", platforms=["youtube_short"], duration_secs=20
        )
        assert result.metadata["mode"] == "ai_video"
        assert result.metadata["topic"] == "هدف الهلال"
        assert "script_id" in result.metadata
        assert result.total_clips_extracted == 2  # 20s / 10s per scene
        assert not result.pipeline_errors

    @pytest.mark.asyncio
    async def test_ai_clips_carry_scene_metadata(self, monkeypatch):
        _clear_env(monkeypatch)
        orch = VideoIntelligenceOrchestrator()
        result = await orch.process_ai_video(
            topic="test", platforms=["youtube_short"], duration_secs=20
        )
        for cr in result.clip_results:
            assert cr.clip.metadata["ai_video"] is True
            assert "scene_id" in cr.clip.metadata
            assert "storyboard_id" in cr.clip.metadata

    def test_build_ai_clips_drops_failed_scenes(self):
        orch = VideoIntelligenceOrchestrator()
        script, board = _script_and_storyboard()
        results = [
            AIVideoResult(provider="p", scene_id="sb-1", status=AIVideoStatus.COMPLETED,
                          public_url="https://x/a.mp4", local_path="/x/a.mp4"),
            AIVideoResult(provider="p", scene_id="sb-2", status=AIVideoStatus.FAILED,
                          error_message="boom"),
        ]
        clips = orch._build_ai_clips("t", script, board, results, "youtube_short")
        assert len(clips) == 1
        assert clips[0].metadata["scene_id"] == "sb-1"

    def test_build_ai_clips_keeps_skipped_scenes_for_dry_run(self):
        orch = VideoIntelligenceOrchestrator()
        script, board = _script_and_storyboard()
        results = [
            AIVideoResult(provider="none", scene_id="sb-1", status=AIVideoStatus.SKIPPED),
            AIVideoResult(provider="none", scene_id="sb-2", status=AIVideoStatus.SKIPPED),
        ]
        clips = orch._build_ai_clips("t", script, board, results, "youtube_short")
        assert len(clips) == 2

    def test_build_ai_clips_timeline_is_contiguous(self):
        orch = VideoIntelligenceOrchestrator()
        script, board = _script_and_storyboard()
        results = [
            AIVideoResult(provider="p", scene_id=f"sb-{i}", status=AIVideoStatus.COMPLETED,
                          public_url=f"https://x/{i}.mp4", local_path=f"/x/{i}.mp4")
            for i in (1, 2)
        ]
        clips = orch._build_ai_clips("t", script, board, results, "youtube_short")
        assert clips[0].start_seconds == 0.0
        assert clips[1].start_seconds == pytest.approx(clips[0].end_seconds)


class TestTimelineGaps:
    def test_no_clips_returns_leading_gap(self):
        orch = VideoIntelligenceOrchestrator()
        gaps = orch._find_timeline_gaps([], total_duration=120.0)
        assert gaps == [(0.0, 60.0)]

    def test_no_duration_returns_no_gaps(self):
        orch = VideoIntelligenceOrchestrator()
        assert orch._find_timeline_gaps([], total_duration=0.0) == []

    def test_gap_between_clips_detected(self):
        from types import SimpleNamespace
        orch = VideoIntelligenceOrchestrator()
        crs = [
            SimpleNamespace(clip=SimpleNamespace(start_seconds=0.0, end_seconds=30.0)),
            SimpleNamespace(clip=SimpleNamespace(start_seconds=100.0, end_seconds=130.0)),
        ]
        gaps = orch._find_timeline_gaps(crs, total_duration=130.0)
        assert gaps == [(30.0, 100.0)]

    def test_small_gaps_below_threshold_ignored(self):
        from types import SimpleNamespace
        orch = VideoIntelligenceOrchestrator()
        crs = [
            SimpleNamespace(clip=SimpleNamespace(start_seconds=0.0, end_seconds=30.0)),
            SimpleNamespace(clip=SimpleNamespace(start_seconds=40.0, end_seconds=70.0)),
        ]
        gaps = orch._find_timeline_gaps(crs, total_duration=70.0)
        assert gaps == []

    def test_trailing_gap_detected(self):
        from types import SimpleNamespace
        orch = VideoIntelligenceOrchestrator()
        crs = [SimpleNamespace(clip=SimpleNamespace(start_seconds=0.0, end_seconds=30.0))]
        gaps = orch._find_timeline_gaps(crs, total_duration=90.0)
        assert gaps == [(30.0, 90.0)]


class TestAutoRouting:
    @pytest.mark.asyncio
    async def test_process_auto_without_source_uses_ai_video(self, monkeypatch):
        _clear_env(monkeypatch)
        orch = VideoIntelligenceOrchestrator()
        # Fresh router so it reads the cleared env
        from sfc.video_intelligence.router.service import VideoProductionRouter
        orch._router = VideoProductionRouter()

        result = await orch.process_auto(topic="test", duration_secs=20)
        assert result.metadata["mode"] == "ai_video"
        decision = result.metadata["router_decision"]
        assert decision["mode"] == "ai_video"
        assert decision["reason"]
        assert not decision["real_footage_available"]
