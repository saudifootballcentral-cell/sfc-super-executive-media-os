"""Tests for AnalyticsSyncLayerService (Package 9C main service)."""

from __future__ import annotations

import os
import pytest

from sfc.analytics_sync.service import AnalyticsSyncLayerService


class TestAnalyticsSyncLayerService:
    def setup_method(self) -> None:
        os.environ.pop("LIVE_PUBLISHING_ENABLED", None)

    @pytest.mark.asyncio
    async def test_sync_dry_run_returns_dict(self) -> None:
        svc = AnalyticsSyncLayerService()
        result = await svc.sync(run_id="test_run_001", period="daily", feed_learning=False)
        assert isinstance(result, dict)
        assert result["run_id"] == "test_run_001"
        assert result["period"] == "daily"
        assert "record_count" in result
        assert "report" in result

    @pytest.mark.asyncio
    async def test_sync_with_video_ids(self) -> None:
        svc = AnalyticsSyncLayerService()
        result = await svc.sync(
            run_id="test_run_002",
            youtube_video_ids=["vid_abc", "vid_xyz"],
            period="daily",
            feed_learning=False,
        )
        # 2 video records + 1 channel-level record (all dry-run zeros)
        assert result["record_count"] >= 2

    @pytest.mark.asyncio
    async def test_sync_with_tweet_ids(self) -> None:
        svc = AnalyticsSyncLayerService()
        result = await svc.sync(
            run_id="test_run_003",
            x_tweet_ids=["tweet_123"],
            period="daily",
            feed_learning=False,
        )
        assert result["record_count"] >= 1

    @pytest.mark.asyncio
    async def test_sync_with_buffer_posts(self) -> None:
        svc = AnalyticsSyncLayerService()
        result = await svc.sync(
            run_id="test_run_004",
            buffer_posts=[{"profile_id": "profile_x", "post_id": "post_abc"}],
            period="daily",
            feed_learning=False,
        )
        assert result["record_count"] >= 1

    @pytest.mark.asyncio
    async def test_sync_all_periods(self) -> None:
        svc = AnalyticsSyncLayerService()
        for period in ("hourly", "daily", "weekly", "monthly", "quarterly"):
            result = await svc.sync(run_id=f"run_{period}", period=period, feed_learning=False)
            assert result["period"] == period

    @pytest.mark.asyncio
    async def test_sync_for_content_youtube(self) -> None:
        svc = AnalyticsSyncLayerService()
        rec = await svc.sync_for_content("vid_abc", "run_sc", platform="youtube")
        assert rec.content_id == "vid_abc"

    @pytest.mark.asyncio
    async def test_sync_for_content_x(self) -> None:
        svc = AnalyticsSyncLayerService()
        rec = await svc.sync_for_content("tweet_xyz", "run_sc", platform="x")
        assert rec.content_id == "tweet_xyz"

    @pytest.mark.asyncio
    async def test_sync_with_learning_does_not_raise(self) -> None:
        svc = AnalyticsSyncLayerService()
        result = await svc.sync(
            run_id="run_learn_test",
            youtube_video_ids=["vid_learn"],
            feed_learning=True,
        )
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_report_included_in_result(self) -> None:
        svc = AnalyticsSyncLayerService()
        result = await svc.sync(run_id="run_report", feed_learning=False)
        report = result["report"]
        assert "report_id" in report
        assert "summary" in report

    @pytest.mark.asyncio
    async def test_top_performers_list(self) -> None:
        svc = AnalyticsSyncLayerService()
        result = await svc.sync(
            run_id="run_top",
            youtube_video_ids=["v1", "v2", "v3"],
            feed_learning=False,
        )
        assert isinstance(result["top_performers"], list)
