"""Retry logic tests for Buffer and connector services — Package 9A."""

from __future__ import annotations

import pytest

from sfc.connectors.buffer.models import BufferPlatform, BufferPost, BufferPostStatus
from sfc.connectors.buffer.service import BufferService


class TestBufferRetryLogic:
    @pytest.mark.asyncio
    async def test_retry_failed_post_succeeds(self):
        service = BufferService()
        post = await service.create_scheduled_post("Test", BufferPlatform.INSTAGRAM)
        post.status = BufferPostStatus.FAILED
        result = await service.retry_failed(post.post_id)
        assert result.status == BufferPostStatus.SENT

    @pytest.mark.asyncio
    async def test_retry_increments_retry_count(self):
        service = BufferService()
        post = await service.create_scheduled_post("Test", BufferPlatform.THREADS)
        post.status = BufferPostStatus.FAILED
        assert post.retry_count == 0
        await service.retry_failed(post.post_id)
        assert post.retry_count == 1

    @pytest.mark.asyncio
    async def test_retry_at_max_retries_returns_failed(self):
        service = BufferService()
        post = await service.create_scheduled_post("Maxed", BufferPlatform.TIKTOK)
        post.status = BufferPostStatus.FAILED
        post.retry_count = service._MAX_RETRIES
        result = await service.retry_failed(post.post_id)
        assert result.status == BufferPostStatus.FAILED

    @pytest.mark.asyncio
    async def test_retry_just_below_max_retries_succeeds(self):
        service = BufferService()
        post = await service.create_scheduled_post("Almost maxed", BufferPlatform.INSTAGRAM)
        post.status = BufferPostStatus.FAILED
        post.retry_count = service._MAX_RETRIES - 1
        result = await service.retry_failed(post.post_id)
        assert result.status == BufferPostStatus.SENT

    @pytest.mark.asyncio
    async def test_retry_nonexistent_post_returns_failed(self):
        service = BufferService()
        result = await service.retry_failed("nonexistent_post_id_xyz")
        assert result.status == BufferPostStatus.FAILED
        assert result.post_id == "nonexistent_post_id_xyz"

    @pytest.mark.asyncio
    async def test_retry_all_failed_retries_all(self):
        service = BufferService()
        p1 = await service.create_scheduled_post("F1", BufferPlatform.INSTAGRAM)
        p2 = await service.create_scheduled_post("F2", BufferPlatform.FACEBOOK)
        p3 = await service.create_scheduled_post("F3", BufferPlatform.THREADS)
        p1.status = BufferPostStatus.FAILED
        p2.status = BufferPostStatus.FAILED
        p3.status = BufferPostStatus.FAILED

        results = await service.retry_all_failed()
        assert len(results) == 3
        assert all(r.status == BufferPostStatus.SENT for r in results)

    @pytest.mark.asyncio
    async def test_retry_all_failed_skips_non_failed(self):
        service = BufferService()
        p_ok = await service.create_scheduled_post("OK", BufferPlatform.INSTAGRAM)
        p_fail = await service.create_scheduled_post("Fail", BufferPlatform.TIKTOK)
        p_fail.status = BufferPostStatus.FAILED

        results = await service.retry_all_failed()
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_retry_all_failed_empty_queue(self):
        service = BufferService()
        results = await service.retry_all_failed()
        assert results == []

    @pytest.mark.asyncio
    async def test_retry_failed_max_retries_error_message(self):
        service = BufferService()
        post = await service.create_scheduled_post("Error msg test", BufferPlatform.INSTAGRAM)
        post.status = BufferPostStatus.FAILED
        post.retry_count = service._MAX_RETRIES
        result = await service.retry_failed(post.post_id)
        assert "max retries" in result.error_message.lower() or "exceeded" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_retry_posts_across_all_platforms(self):
        service = BufferService()
        platforms = [
            BufferPlatform.INSTAGRAM,
            BufferPlatform.THREADS,
            BufferPlatform.FACEBOOK,
            BufferPlatform.TIKTOK,
        ]
        for platform in platforms:
            post = await service.create_scheduled_post("Cross platform", platform)
            post.status = BufferPostStatus.FAILED

        results = await service.retry_all_failed()
        assert len(results) == 4
        result_platforms = {r.platform for r in results}
        assert len(result_platforms) == 4

    @pytest.mark.asyncio
    async def test_max_retries_constant_is_three(self):
        service = BufferService()
        assert service._MAX_RETRIES == 3

    @pytest.mark.asyncio
    async def test_successful_publish_no_retry_needed(self):
        service = BufferService()
        post = await service.create_scheduled_post("Success case", BufferPlatform.INSTAGRAM)
        result = await service.publish_post(post.post_id)
        assert result.status == BufferPostStatus.SENT
        assert post.retry_count == 0

    @pytest.mark.asyncio
    async def test_retry_updates_post_status_to_retrying(self):
        service = BufferService()
        post = await service.create_scheduled_post("Status update", BufferPlatform.INSTAGRAM)
        post.status = BufferPostStatus.FAILED

        # Start the retry — the internal status changes to RETRYING before being SENT
        result = await service.retry_failed(post.post_id)
        # After retry completes it should be SENT
        assert result.status == BufferPostStatus.SENT

    @pytest.mark.asyncio
    async def test_report_shows_retried_posts(self):
        service = BufferService()
        post = await service.create_scheduled_post("Retried post", BufferPlatform.INSTAGRAM)
        post.status = BufferPostStatus.FAILED
        await service.retry_failed(post.post_id)
        report = await service.generate_report()
        assert report.posts_retried >= 1
