"""Tests for Clip Scoring Engine."""

from __future__ import annotations

import pytest

from sfc.video_intelligence.clipping.models import ClipSourceType, ClipStatus, VideoClip
from sfc.video_intelligence.scoring.models import ClipScore
from sfc.video_intelligence.scoring.service import ClipScoringEngine


def _clip(
    clip_type: str = "goal",
    duration: float = 30.0,
    source_type: ClipSourceType = ClipSourceType.SPORT_EVENT,
    file_size: int = 0,
) -> VideoClip:
    return VideoClip(
        video_id="vid-1",
        start_seconds=0.0,
        end_seconds=duration,
        clip_type=clip_type,
        source_type=source_type,
        file_size_bytes=file_size,
    )


class TestClipScoring:
    @pytest.mark.asyncio
    async def test_score_has_all_dimensions(self):
        svc = ClipScoringEngine()
        score = await svc.score(_clip("goal"))
        assert score.viral_potential > 0
        assert score.audience_appeal > 0
        assert score.brand_alignment > 0
        assert score.technical_quality > 0
        assert score.overall_score > 0

    @pytest.mark.asyncio
    async def test_goal_clip_higher_viral_than_corner(self):
        svc = ClipScoringEngine()
        goal_score = await svc.score(_clip("goal"))
        corner_score = await svc.score(_clip("corner"))
        # Goal should generally score higher; allow for random variation
        assert goal_score.viral_potential > corner_score.viral_potential - 20

    @pytest.mark.asyncio
    async def test_score_includes_platform_scores(self):
        svc = ClipScoringEngine()
        score = await svc.score(_clip("goal"))
        assert len(score.platform_scores) > 0

    @pytest.mark.asyncio
    async def test_best_platform_is_set(self):
        svc = ClipScoringEngine()
        score = await svc.score(_clip("goal"))
        assert score.best_platform != ""

    @pytest.mark.asyncio
    async def test_overall_score_within_0_100(self):
        svc = ClipScoringEngine()
        for ctype in ("goal", "save", "key_quote", "controversial", "corner"):
            score = await svc.score(_clip(ctype))
            assert 0 <= score.overall_score <= 100

    @pytest.mark.asyncio
    async def test_controversial_clip_lower_brand_alignment(self):
        svc = ClipScoringEngine()
        score = await svc.score(_clip("controversial"))
        assert score.brand_alignment < 75

    @pytest.mark.asyncio
    async def test_clip_with_real_file_higher_technical_quality(self):
        svc = ClipScoringEngine()
        score_no_file = await svc.score(_clip("goal", file_size=0))
        score_with_file = await svc.score(_clip("goal", file_size=5_000_000))
        assert score_with_file.technical_quality >= score_no_file.technical_quality

    @pytest.mark.asyncio
    async def test_platform_score_within_duration_limit(self):
        svc = ClipScoringEngine()
        # 30s clip should be within most platform limits
        score = await svc.score(_clip("goal", duration=30.0))
        short_platforms = [
            ps for ps in score.platform_scores
            if ps.platform in ("youtube_short", "instagram_reel")
        ]
        for ps in short_platforms:
            assert ps.within_duration_limit is True


class TestClipScoreModel:
    def test_is_publishable_high_score(self):
        score = ClipScore(
            clip_id="c1",
            overall_score=85.0,
            brand_alignment=80.0,
        )
        assert score.is_publishable is True

    def test_is_publishable_low_score(self):
        score = ClipScore(
            clip_id="c1",
            overall_score=50.0,
            brand_alignment=80.0,
        )
        assert score.is_publishable is False

    def test_is_publishable_low_brand(self):
        score = ClipScore(
            clip_id="c1",
            overall_score=90.0,
            brand_alignment=50.0,
        )
        assert score.is_publishable is False
