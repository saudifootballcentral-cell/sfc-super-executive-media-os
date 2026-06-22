"""Tests for Buffer API connector (Package 9A)."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from sfc.connectors.buffer.models import (
    BufferConnectorReport,
    BufferMultiPlatformRequest,
    BufferPlatform,
    BufferPost,
    BufferPostStatus,
    BufferPublishResult,
    BufferQueue,
)
from sfc.connectors.buffer.service import BufferService, get_buffer_service


class TestBufferModels:
    def test_buffer_post_defaults(self):
        post = BufferPost(content="Test", platform=BufferPlatform.INSTAGRAM)
        assert post.post_id
        assert post.retry_count == 0
        assert post.status == BufferPostStatus.SCHEDULED

    def test_buffer_post_to_summary(self):
        post = BufferPost(content="Test post content", platform=BufferPlatform.TIKTOK)
        summary = post.to_summary()
        assert "tiktok" in summary

    def test_buffer_publish_result_to_dict(self):
        result = BufferPublishResult(
            post_id="p1", platform=BufferPlatform.INSTAGRAM, status=BufferPostStatus.SENT
        )
        d = result.to_dict()
        assert d["platform"] == "instagram"
        assert d["status"] == "sent"

    def test_buffer_queue_to_dict(self):
        q = BufferQueue(pending_count=2, scheduled_count=5, sent_count=10)
        d = q.to_dict()
        assert d["pending_count"] == 2
        assert d["sent_count"] == 10


class TestBufferService:
    @pytest.mark.asyncio
    async def test_create_scheduled_post(self):
        service = BufferService()
        post = await service.create_scheduled_post(
            content="SPL Highlights! #SFC",
            platform=BufferPlatform.INSTAGRAM,
        )
        assert post.status == BufferPostStatus.SCHEDULED
        assert post.scheduled_at is not None

    @pytest.mark.asyncio
    async def test_scheduled_at_defaults_to_future(self):
        service = BufferService()
        post = await service.create_scheduled_post("Test", BufferPlatform.INSTAGRAM)
        assert post.scheduled_at > datetime.utcnow()

    @pytest.mark.asyncio
    async def test_publish_post(self):
        service = BufferService()
        post = await service.create_scheduled_post("Test", BufferPlatform.THREADS)
        result = await service.publish_post(post.post_id)
        assert result.status == BufferPostStatus.SENT
        assert result.platform_post_id != ""

    @pytest.mark.asyncio
    async def test_publish_to_platforms(self):
        service = BufferService()
        results = await service.publish_to_platforms(
            content="Multi-platform post",
            platforms=[BufferPlatform.INSTAGRAM, BufferPlatform.TIKTOK],
        )
        assert len(results) == 2
        assert all(r.status == BufferPostStatus.SENT for r in results)

    @pytest.mark.asyncio
    async def test_get_queue(self):
        service = BufferService()
        await service.create_scheduled_post("Q1", BufferPlatform.INSTAGRAM)
        await service.create_scheduled_post("Q2", BufferPlatform.FACEBOOK)
        queue = await service.get_queue()
        assert isinstance(queue, BufferQueue)
        assert queue.scheduled_count >= 2

    @pytest.mark.asyncio
    async def test_get_status(self):
        service = BufferService()
        post = await service.create_scheduled_post("Status test", BufferPlatform.INSTAGRAM)
        found = await service.get_status(post.post_id)
        assert found is not None
        assert found.post_id == post.post_id

    @pytest.mark.asyncio
    async def test_retry_failed_post(self):
        service = BufferService()
        post = await service.create_scheduled_post("Retry test", BufferPlatform.TIKTOK)
        post.status = BufferPostStatus.FAILED
        result = await service.retry_failed(post.post_id)
        assert result.status == BufferPostStatus.SENT

    @pytest.mark.asyncio
    async def test_retry_exceeds_max_retries(self):
        service = BufferService()
        post = await service.create_scheduled_post("Max retry", BufferPlatform.INSTAGRAM)
        post.status = BufferPostStatus.FAILED
        post.retry_count = service._MAX_RETRIES
        result = await service.retry_failed(post.post_id)
        assert result.status == BufferPostStatus.FAILED

    @pytest.mark.asyncio
    async def test_retry_all_failed(self):
        service = BufferService()
        p1 = await service.create_scheduled_post("F1", BufferPlatform.INSTAGRAM)
        p2 = await service.create_scheduled_post("F2", BufferPlatform.THREADS)
        p1.status = BufferPostStatus.FAILED
        p2.status = BufferPostStatus.FAILED
        results = await service.retry_all_failed()
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_publish_content_package(self):
        service = BufferService()
        package = {
            "package_type": "instagram",
            "caption": "Match day! ⚽ #SFC",
            "hashtags": ["#SFC", "#Saudi"],
            "thumbnail_url": "https://example.com/thumb.jpg",
            "ready_to_publish": True,
        }
        results = await service.publish_content_package(package)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_generate_report(self):
        service = BufferService()
        await service.publish_to_platforms("Test", [BufferPlatform.INSTAGRAM])
        report = await service.generate_report()
        assert isinstance(report, BufferConnectorReport)
        assert report.posts_published >= 1
        assert report.success_rate >= 0

    def test_not_authenticated_without_env(self):
        service = BufferService()
        assert service.is_authenticated is False

    def test_singleton(self):
        s1 = get_buffer_service()
        s2 = get_buffer_service()
        assert s1 is s2
