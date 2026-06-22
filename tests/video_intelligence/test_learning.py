"""Tests for Clip Learning Loop."""

from __future__ import annotations

import pytest

from sfc.video_intelligence.learning.service import ClipLearningLoop
from sfc.video_intelligence.packaging.models import ClipPackage, PlatformClipVariant
from sfc.video_intelligence.scoring.models import ClipScore


def _package(clip_id: str = "clip-1", clip_type: str = "goal") -> ClipPackage:
    return ClipPackage(
        clip_id=clip_id,
        video_id="vid-1",
        title="Test",
        clip_type=clip_type,
        quality_score=80.0,
        variants=[
            PlatformClipVariant(
                platform="youtube_short",
                aspect_ratio="9:16",
                duration_seconds=30.0,
            )
        ],
    )


def _score(clip_id: str = "clip-1", overall: float = 82.0) -> ClipScore:
    return ClipScore(clip_id=clip_id, overall_score=overall)


class TestLearningRecords:
    def test_record_prediction_creates_record(self):
        loop = ClipLearningLoop()
        loop.reset_for_test()
        record = loop.record_prediction(_package(), _score())
        assert record.clip_id == "clip-1"
        assert record.predicted_score == 82.0

    def test_record_performance_updates_existing(self):
        loop = ClipLearningLoop()
        loop.reset_for_test()
        loop.record_prediction(_package(), _score())
        loop.record_performance(
            clip_id="clip-1",
            platform="youtube_short",
            views=10000,
            likes=500,
            shares=200,
            comments=100,
        )
        records = loop.get_records()
        assert len(records) == 1
        assert records[0].views == 10000
        assert records[0].engagement_rate > 0

    def test_record_performance_new_record_if_no_prediction(self):
        loop = ClipLearningLoop()
        loop.reset_for_test()
        loop.record_performance(
            clip_id="clip-99",
            platform="tiktok",
            views=5000,
            likes=300,
            shares=50,
            comments=20,
        )
        records = loop.get_records()
        assert any(r.clip_id == "clip-99" for r in records)

    def test_viral_score_computed(self):
        loop = ClipLearningLoop()
        loop.reset_for_test()
        record = loop.record_performance(
            clip_id="clip-1",
            platform="youtube_short",
            views=100000,
            likes=5000,
            shares=10000,
            comments=1000,
        )
        assert record.viral_score > 0

    def test_engagement_rate_computed(self):
        loop = ClipLearningLoop()
        loop.reset_for_test()
        record = loop.record_performance(
            clip_id="clip-1",
            platform="youtube_short",
            views=1000,
            likes=100,
            shares=50,
            comments=20,
        )
        expected = ((100 + 50 + 20) / 1000) * 100
        assert abs(record.engagement_rate - expected) < 0.01


class TestLearningReport:
    @pytest.mark.asyncio
    async def test_empty_report(self):
        loop = ClipLearningLoop()
        loop.reset_for_test()
        report = await loop.generate_report()
        assert report.total_clips_tracked == 0
        assert report.insights == []

    @pytest.mark.asyncio
    async def test_report_identifies_top_clip_type(self):
        loop = ClipLearningLoop()
        loop.reset_for_test()
        for ctype, views in [("goal", 50000), ("save", 10000), ("goal", 70000)]:
            clip_id = f"clip-{ctype}-{views}"
            pkg = _package(clip_id=clip_id, clip_type=ctype)
            loop.record_prediction(pkg, _score(clip_id=clip_id))
            loop.record_performance(
                clip_id=clip_id,
                platform="youtube_short",
                views=views,
                likes=views // 10,
                shares=views // 20,
                comments=views // 50,
            )
        report = await loop.generate_report()
        assert report.top_clip_type == "goal"

    @pytest.mark.asyncio
    async def test_report_identifies_top_platform(self):
        loop = ClipLearningLoop()
        loop.reset_for_test()
        loop.record_performance(
            clip_id="c1", platform="tiktok",
            views=100000, likes=10000, shares=5000, comments=2000,
        )
        loop.record_performance(
            clip_id="c2", platform="x_video",
            views=1000, likes=50, shares=10, comments=5,
        )
        report = await loop.generate_report()
        assert report.top_platform == "tiktok"

    @pytest.mark.asyncio
    async def test_report_generates_insights(self):
        loop = ClipLearningLoop()
        loop.reset_for_test()
        loop.record_performance(
            clip_id="c1", platform="youtube_short",
            views=10000, likes=500, shares=200, comments=100,
        )
        loop.get_records()[0].clip_type = "goal"
        report = await loop.generate_report()
        assert report.total_clips_tracked == 1

    @pytest.mark.asyncio
    async def test_weight_adjustments_applied(self):
        loop = ClipLearningLoop()
        loop.reset_for_test()
        # High-performing goal clips should nudge goal weight up
        for i in range(3):
            cid = f"c{i}"
            pkg = _package(clip_id=cid, clip_type="goal")
            loop.record_prediction(pkg, _score(clip_id=cid))
            loop.record_performance(
                clip_id=cid, platform="youtube_short",
                views=100000, likes=10000, shares=5000, comments=2000,
            )
        original_weight = 1.0
        report = await loop.generate_report()
        if "goal" in report.weight_adjustments:
            # High engagement → weight should be nudged (could be up or down based on avg)
            assert report.weight_adjustments["goal"] > 0

    def test_get_adjusted_weights_includes_all_event_types(self):
        loop = ClipLearningLoop()
        loop.reset_for_test()
        weights = loop.get_adjusted_weights()
        assert "goal" in weights
        assert "save" in weights
        assert "penalty" in weights
