"""End-to-end integration test for Package 9B + 9C pipeline (dry-run mode)."""

from __future__ import annotations

import os
import pytest

from sfc.analytics_sync.service import AnalyticsSyncLayerService
from sfc.connectors.buffer.models import BufferPlatform, BufferPost, BufferPostStatus
from sfc.connectors.buffer.publisher import BufferPublisher, PublishApprovalError
from sfc.connectors.buffer.service import BufferService


class TestPkg9B9CIntegration:
    def setup_method(self) -> None:
        # Ensure dry-run mode
        os.environ.pop("LIVE_PUBLISHING_ENABLED", None)

    # ------------------------------------------------------------------
    # 9B: Full publish + analytics loop
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_buffer_service_dry_run_publish(self) -> None:
        """BufferService mock path: create post → publish → verify sent status."""
        svc = BufferService()
        post = await svc.create_scheduled_post(
            content="Goal! Al-Hilal 1-0 Al-Nassr",
            platform=BufferPlatform.INSTAGRAM,
            hashtags=["AlHilal", "SPL"],
        )
        assert post.status == BufferPostStatus.SCHEDULED
        result = await svc.publish_post(post.post_id)
        assert result.status == BufferPostStatus.SENT
        assert result.platform_post_id != ""

    @pytest.mark.asyncio
    async def test_buffer_publish_to_x_and_youtube(self) -> None:
        """Both X and YouTube platforms now supported in BufferService."""
        svc = BufferService()
        results = await svc.publish_to_platforms(
            content="Match highlight: penalty saved!",
            platforms=[BufferPlatform.X, BufferPlatform.YOUTUBE],
            hashtags=["SPL", "Football"],
        )
        assert len(results) == 2
        platforms_published = {r.platform for r in results}
        assert BufferPlatform.X in platforms_published
        assert BufferPlatform.YOUTUBE in platforms_published

    @pytest.mark.asyncio
    async def test_triple_lock_blocks_without_governance(self) -> None:
        """Publisher blocks if governance_approved=False."""
        publisher = BufferPublisher()
        post = BufferPost(content="Test", platform=BufferPlatform.X)
        with pytest.raises(PublishApprovalError):
            await publisher.create_post(
                post, "profile_x",
                governance_approved=False,
                operator_approved=True,
                rights_status="owned",
            )

    @pytest.mark.asyncio
    async def test_triple_lock_passes_with_all_approved(self) -> None:
        """Publisher dry-runs correctly when all gates pass."""
        publisher = BufferPublisher()
        post = BufferPost(content="SPL Goal!", platform=BufferPlatform.X, hashtags=["SPL"])
        result = await publisher.create_post(
            post, "profile_x",
            governance_approved=True,
            operator_approved=True,
            rights_status="owned",
        )
        assert result.platform_post_id.startswith("dry_")

    @pytest.mark.asyncio
    async def test_retry_manager_exhaustion_raises(self) -> None:
        """RetryManager stops after configured attempts."""
        from sfc.connectors.buffer.api_client import BufferAPIError
        from sfc.connectors.buffer.retry_manager import BufferRetryManager
        manager = BufferRetryManager(delays_seconds=[0, 0])
        attempts = 0

        async def always_fail() -> None:
            nonlocal attempts
            attempts += 1
            raise BufferAPIError("server error", status_code=500, permanent=False)

        with pytest.raises(BufferAPIError):
            await manager.call_with_retry("e2e_key", always_fail, skip_wait=True)
        assert attempts == 3  # initial + 2 retries

    # ------------------------------------------------------------------
    # 9C: Analytics sync cycle
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_analytics_sync_full_cycle(self) -> None:
        """Full analytics sync cycle with YouTube + X + Buffer sources."""
        svc = AnalyticsSyncLayerService()
        result = await svc.sync(
            run_id="e2e_sync_001",
            youtube_video_ids=["yt_goal_123"],
            x_tweet_ids=["tweet_456"],
            buffer_posts=[{"profile_id": "buf_prof", "post_id": "buf_post_789"}],
            period="daily",
            feed_learning=True,
        )
        assert result["run_id"] == "e2e_sync_001"
        assert result["period"] == "daily"
        assert result["record_count"] >= 3
        assert isinstance(result["report"], dict)
        assert isinstance(result["top_performers"], list)
        assert isinstance(result["optimizations"], list)

    @pytest.mark.asyncio
    async def test_analytics_sync_report_has_summary(self) -> None:
        svc = AnalyticsSyncLayerService()
        result = await svc.sync(run_id="e2e_sync_002", period="weekly", feed_learning=False)
        report = result["report"]
        assert "summary" in report
        assert "total_views" in report["summary"]

    @pytest.mark.asyncio
    async def test_publish_then_sync(self) -> None:
        """Simulate publish followed by analytics sync — the key 9B→9C flow."""
        # Step 1: Publish content via Buffer (dry-run)
        buf_svc = BufferService()
        post = await buf_svc.create_scheduled_post(
            content="SPL Final: Penalty! Goal!",
            platform=BufferPlatform.X,
        )
        publish_result = await buf_svc.publish_post(post.post_id)
        assert publish_result.status == BufferPostStatus.SENT

        # Step 2: Sync analytics for the published post
        analytics_svc = AnalyticsSyncLayerService()
        sync_result = await analytics_svc.sync(
            run_id="e2e_publish_then_sync",
            x_tweet_ids=[publish_result.platform_post_id],
            period="daily",
            feed_learning=False,
        )
        assert sync_result["record_count"] >= 1

    @pytest.mark.asyncio
    async def test_buffer_report_after_multiple_publishes(self) -> None:
        """BufferService generates accurate report after multi-platform publish."""
        svc = BufferService()
        await svc.publish_to_platforms(
            content="Match stats: Al-Hilal dominate",
            platforms=[BufferPlatform.INSTAGRAM, BufferPlatform.FACEBOOK, BufferPlatform.X],
        )
        report = await svc.generate_report()
        assert report.posts_published >= 3
        assert report.success_rate == 100.0
        assert len(report.platforms_active) >= 3
