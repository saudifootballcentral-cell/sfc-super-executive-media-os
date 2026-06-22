"""Tests for Package 9C analytics providers (dry-run mode)."""

from __future__ import annotations

import os
import pytest

from sfc.analytics_sync.aggregation.models import AnalyticsPlatform
from sfc.analytics_sync.providers.buffer import BufferAnalyticsProvider
from sfc.analytics_sync.providers.x import XAnalyticsProvider
from sfc.analytics_sync.providers.youtube import YouTubeAnalyticsProvider


class TestYouTubeProviderDryRun:
    def setup_method(self) -> None:
        os.environ.pop("LIVE_PUBLISHING_ENABLED", None)

    @pytest.mark.asyncio
    async def test_fetch_video_dry_run(self) -> None:
        provider = YouTubeAnalyticsProvider()
        rec = await provider.fetch_video_metrics("video123", run_id="run_test")
        assert rec.content_id == "video123"
        assert rec.platform == AnalyticsPlatform.YOUTUBE
        assert rec.raw.get("dry_run") is True

    @pytest.mark.asyncio
    async def test_fetch_channel_dry_run(self) -> None:
        provider = YouTubeAnalyticsProvider()
        rec = await provider.fetch_channel_metrics(run_id="run_test")
        assert rec.content_id == "channel"
        assert rec.platform == AnalyticsPlatform.YOUTUBE

    @pytest.mark.asyncio
    async def test_dry_run_engagement_rate_zero(self) -> None:
        provider = YouTubeAnalyticsProvider()
        rec = await provider.fetch_video_metrics("vid1", run_id="r1")
        # 0 views → engagement_rate stays 0
        assert rec.engagement_rate == 0.0


class TestXProviderDryRun:
    def setup_method(self) -> None:
        os.environ.pop("LIVE_PUBLISHING_ENABLED", None)

    @pytest.mark.asyncio
    async def test_fetch_tweet_dry_run(self) -> None:
        provider = XAnalyticsProvider()
        rec = await provider.fetch_tweet_metrics("tweet_abc", run_id="run_x")
        assert rec.content_id == "tweet_abc"
        assert rec.platform == AnalyticsPlatform.X
        assert rec.raw.get("dry_run") is True

    @pytest.mark.asyncio
    async def test_fetch_account_dry_run(self) -> None:
        provider = XAnalyticsProvider()
        rec = await provider.fetch_account_metrics(run_id="run_x")
        assert rec.content_id == "account"

    @pytest.mark.asyncio
    async def test_dry_run_has_zero_metrics(self) -> None:
        provider = XAnalyticsProvider()
        rec = await provider.fetch_tweet_metrics("t1", run_id="r1")
        assert rec.views == 0
        assert rec.likes == 0


class TestBufferProviderDryRun:
    def setup_method(self) -> None:
        os.environ.pop("LIVE_PUBLISHING_ENABLED", None)

    @pytest.mark.asyncio
    async def test_fetch_post_dry_run(self) -> None:
        provider = BufferAnalyticsProvider()
        rec = await provider.fetch_post_metrics("profile_123", "post_456", run_id="run_buf")
        assert rec.content_id == "post_456"
        assert rec.platform == AnalyticsPlatform.BUFFER
        assert rec.raw.get("dry_run") is True

    @pytest.mark.asyncio
    async def test_fetch_channel_performance_dry_run(self) -> None:
        provider = BufferAnalyticsProvider()
        records = await provider.fetch_channel_performance("profile_123", run_id="r1")
        # dry-run returns empty list
        assert records == []
