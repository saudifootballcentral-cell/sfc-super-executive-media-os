"""End-to-end publishing flow tests — Package 9A."""

from __future__ import annotations

import pytest

from sfc.connectors.buffer.models import BufferPlatform, BufferPostStatus
from sfc.connectors.buffer.service import BufferService
from sfc.connectors.x.models import XPostStatus
from sfc.connectors.x.service import XService
from sfc.connectors.youtube.models import UploadStatus, VideoUploadRequest
from sfc.connectors.youtube.service import YouTubeService


class TestYouTubePublishingFlow:
    @pytest.mark.asyncio
    async def test_upload_and_get_analytics(self):
        service = YouTubeService()
        req = VideoUploadRequest(title="SPL Final Highlights")
        result = await service.upload_video(req)
        assert result.status == UploadStatus.PUBLISHED

        analytics = await service.get_analytics(result.video_id)
        assert analytics.views > 0
        assert analytics.video_id == result.video_id

    @pytest.mark.asyncio
    async def test_upload_short_and_verify_url(self):
        service = YouTubeService()
        req = VideoUploadRequest(title="Goal Compilation", is_short=True)
        result = await service.upload_short(req)
        assert result.is_short is True
        assert "youtube.com" in result.url

    @pytest.mark.asyncio
    async def test_full_video_lifecycle(self):
        service = YouTubeService()
        req = VideoUploadRequest(title="Match Report", description="Full match coverage")
        result = await service.upload_video(req)
        video_id = result.video_id

        ok_meta = await service.update_metadata(video_id, title="Match Report (Updated)")
        ok_thumb = await service.update_thumbnail(video_id, "https://cdn.example.com/thumb.jpg")
        analytics = await service.get_analytics(video_id)
        comments = await service.get_comments(video_id, max_results=3)

        assert ok_meta is True
        assert ok_thumb is True
        assert analytics.views > 0
        assert len(comments) > 0

    @pytest.mark.asyncio
    async def test_playlist_with_multiple_uploads(self):
        service = YouTubeService()
        ids: list[str] = []
        for i in range(3):
            req = VideoUploadRequest(title=f"SPL Round {i+1}")
            result = await service.upload_video(req)
            ids.append(result.video_id)

        playlist = await service.create_playlist("SPL Season Highlights", video_ids=ids)
        assert playlist.item_count == 3
        assert len(playlist.video_ids) == 3

    @pytest.mark.asyncio
    async def test_report_reflects_uploads(self):
        service = YouTubeService()
        await service.upload_video(VideoUploadRequest(title="Video A"))
        await service.upload_short(VideoUploadRequest(title="Short A", is_short=True))
        report = await service.generate_report()
        assert report.videos_published >= 1
        assert report.shorts_published >= 1
        assert report.channel_metrics is not None


class TestXPublishingFlow:
    @pytest.mark.asyncio
    async def test_create_post_and_get_metrics(self):
        service = XService()
        post = await service.create_post("SPL Round 15 kicks off! #SaudiProLeague")
        assert post.status == XPostStatus.PUBLISHED
        assert post.platform_post_id != ""

        metrics = await service.get_metrics(post.platform_post_id)
        assert metrics.views > 0
        assert metrics.impressions > 0

    @pytest.mark.asyncio
    async def test_thread_all_posts_linked(self):
        service = XService()
        thread = await service.create_thread(
            texts=["Part 1: The build-up", "Part 2: The match", "Part 3: Aftermath"],
            topic="Match Analysis",
        )
        assert thread.total_posts == 3
        assert thread.platform_thread_root_id != ""
        assert all(p.status == XPostStatus.PUBLISHED for p in thread.posts)

    @pytest.mark.asyncio
    async def test_media_upload_then_post(self):
        from sfc.connectors.x.models import XMediaType
        service = XService()
        media = await service.upload_media("https://example.com/image.jpg", XMediaType.IMAGE)
        post = await service.create_post(
            "Match photo #SaudiFootball",
            media_ids=[media.platform_media_id],
        )
        assert post.status == XPostStatus.PUBLISHED
        assert len(post.media_ids) == 1

    @pytest.mark.asyncio
    async def test_social_intelligence_pipeline(self):
        service = XService()
        trends = await service.get_trending_topics()
        keywords = await service.monitor_keywords(["SPL", "AlHilal"])
        hashtags = await service.monitor_hashtags(["#SaudiProLeague"])
        conversations = await service.search_conversations("football", max_results=3)

        assert len(trends) > 0
        assert len(keywords) > 0
        assert len(hashtags) > 0
        assert len(conversations) > 0

    @pytest.mark.asyncio
    async def test_report_after_posts(self):
        service = XService()
        await service.create_post("Post one #SFC")
        await service.create_post("Post two #SFC")
        report = await service.generate_report()
        assert report.posts_published >= 2
        assert report.total_impressions >= 0


class TestBufferPublishingFlow:
    @pytest.mark.asyncio
    async def test_multi_platform_publish(self):
        service = BufferService()
        results = await service.publish_to_platforms(
            content="Match day content! #SFC",
            platforms=[BufferPlatform.INSTAGRAM, BufferPlatform.THREADS, BufferPlatform.FACEBOOK],
        )
        assert len(results) == 3
        assert all(r.status == BufferPostStatus.SENT for r in results)

    @pytest.mark.asyncio
    async def test_content_package_instagram_type(self):
        service = BufferService()
        package = {
            "package_type": "instagram",
            "caption": "Goal of the month! ⚽",
            "hashtags": ["#SFC", "#SPL"],
            "thumbnail_url": "https://cdn.example.com/goal.jpg",
            "ready_to_publish": True,
        }
        results = await service.publish_content_package(package)
        assert len(results) >= 1
        platforms = {r.platform.value for r in results}
        assert "instagram" in platforms

    @pytest.mark.asyncio
    async def test_content_package_tiktok_type(self):
        service = BufferService()
        package = {
            "package_type": "tiktok",
            "caption": "TikTok reel",
            "ready_to_publish": True,
        }
        results = await service.publish_content_package(package)
        assert len(results) >= 1
        assert any(r.platform == BufferPlatform.TIKTOK for r in results)

    @pytest.mark.asyncio
    async def test_queue_grows_with_scheduled_posts(self):
        service = BufferService()
        for i in range(4):
            await service.create_scheduled_post(f"Post {i}", BufferPlatform.INSTAGRAM)
        queue = await service.get_queue()
        assert queue.scheduled_count >= 4

    @pytest.mark.asyncio
    async def test_report_success_rate_full(self):
        service = BufferService()
        await service.publish_to_platforms("Content", [BufferPlatform.INSTAGRAM])
        report = await service.generate_report()
        assert report.success_rate == 100.0
        assert report.posts_published >= 1


class TestCrossPlatformPublishingFlow:
    @pytest.mark.asyncio
    async def test_youtube_and_x_publish_in_sequence(self):
        yt = YouTubeService()
        x = XService()

        yt_result = await yt.upload_video(VideoUploadRequest(title="SPL Preview"))
        x_post = await x.create_post(f"Now live: SPL Preview on YouTube! {yt_result.url}")

        assert yt_result.status == UploadStatus.PUBLISHED
        assert x_post.status == XPostStatus.PUBLISHED
        assert yt_result.url in x_post.text

    @pytest.mark.asyncio
    async def test_youtube_short_also_queued_to_instagram_via_buffer(self):
        yt = YouTubeService()
        buf = BufferService()

        short = await yt.upload_short(VideoUploadRequest(title="Reel content", is_short=True))
        assert short.is_short is True

        results = await buf.publish_to_platforms(
            content="Check out our new reel!",
            platforms=[BufferPlatform.INSTAGRAM],
            media_url=short.url,
        )
        assert results[0].status == BufferPostStatus.SENT
