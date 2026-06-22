"""Tests for Video Ingestion Layer."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from sfc.video_intelligence.ingestion.models import (
    RightsStatus,
    VideoIngestionResult,
    VideoProcessingStatus,
    VideoSource,
    VideoSourceType,
    VideoResolution,
)
from sfc.video_intelligence.ingestion.service import VideoIngestionService


def _svc() -> VideoIngestionService:
    svc = VideoIngestionService()
    svc.reset_for_test()
    return svc


def _source(
    title: str = "Test Match",
    source_type: VideoSourceType = VideoSourceType.MATCH_RECORDING,
    rights: RightsStatus = RightsStatus.OWNED,
    path: str = "",
    url: str = "",
) -> VideoSource:
    return VideoSource(
        source_type=source_type,
        title=title,
        rights_status=rights,
        path=path,
        url=url,
    )


class TestIngestionDryRun:
    @pytest.mark.asyncio
    async def test_dry_run_returns_dry_run_status(self):
        svc = _svc()
        with patch.dict(os.environ, {"VIDEO_PROCESSING_ENABLED": "false"}):
            result = await svc.ingest(_source())
        assert result.status == VideoProcessingStatus.DRY_RUN
        assert result.video_metadata is not None
        assert result.video_metadata.metadata.get("dry_run") is True

    @pytest.mark.asyncio
    async def test_dry_run_returns_mock_metadata(self):
        svc = _svc()
        with patch.dict(os.environ, {"VIDEO_PROCESSING_ENABLED": "false"}):
            result = await svc.ingest(_source(title="Goal Compilation"))
        assert result.video_metadata is not None
        assert result.video_metadata.title == "Goal Compilation"
        assert result.video_metadata.duration_seconds == 120.0

    @pytest.mark.asyncio
    async def test_dry_run_succeeded_is_true(self):
        svc = _svc()
        with patch.dict(os.environ, {"VIDEO_PROCESSING_ENABLED": "false"}):
            result = await svc.ingest(_source())
        assert result.succeeded is True


class TestRightsGating:
    @pytest.mark.asyncio
    async def test_restricted_source_is_blocked(self):
        svc = _svc()
        result = await svc.ingest(_source(rights=RightsStatus.RESTRICTED))
        assert result.status == VideoProcessingStatus.RIGHTS_BLOCKED
        assert result.succeeded is False
        assert "RESTRICTED" in result.error_message

    @pytest.mark.asyncio
    async def test_restricted_source_not_in_hash_index(self):
        svc = _svc()
        await svc.ingest(_source(rights=RightsStatus.RESTRICTED))
        assert len(svc._hash_index) == 0

    @pytest.mark.asyncio
    async def test_owned_source_is_not_blocked(self):
        svc = _svc()
        with patch.dict(os.environ, {"VIDEO_PROCESSING_ENABLED": "false"}):
            result = await svc.ingest(_source(rights=RightsStatus.OWNED))
        assert result.status != VideoProcessingStatus.RIGHTS_BLOCKED

    @pytest.mark.asyncio
    async def test_unknown_rights_not_blocked_in_ingestion(self):
        """Unknown rights are allowed in ingestion; publishing is blocked later."""
        svc = _svc()
        with patch.dict(os.environ, {"VIDEO_PROCESSING_ENABLED": "false"}):
            result = await svc.ingest(_source(rights=RightsStatus.UNKNOWN))
        assert result.status != VideoProcessingStatus.RIGHTS_BLOCKED


class TestDeduplication:
    @pytest.mark.asyncio
    async def test_same_url_is_deduplicated(self):
        svc = _svc()
        src = _source(url="http://example.com/match.mp4")
        with patch.dict(os.environ, {"VIDEO_PROCESSING_ENABLED": "true"}):
            r1 = await svc.ingest(src)
            r2 = await svc.ingest(
                VideoSource(
                    source_type=VideoSourceType.MATCH_RECORDING,
                    url="http://example.com/match.mp4",
                    rights_status=RightsStatus.OWNED,
                )
            )
        # First ingestion not duplicate; second should detect duplicate hash
        assert r1.is_duplicate is False
        assert r2.is_duplicate is True
        assert r2.status == VideoProcessingStatus.DUPLICATE
        assert r2.duplicate_of is not None


class TestVideoMetadata:
    def test_resolution_label(self):
        res = VideoResolution(width=1920, height=1080)
        assert res.label == "1080p"

    def test_resolution_label_4k(self):
        res = VideoResolution(width=3840, height=2160)
        assert res.label == "4K"

    def test_resolution_label_720p(self):
        res = VideoResolution(width=1280, height=720)
        assert res.label == "720p"

    def test_is_publishable_rights_owned(self):
        from sfc.video_intelligence.ingestion.models import VideoMetadata
        meta = VideoMetadata(rights_status=RightsStatus.OWNED)
        assert meta.is_publishable_rights is True

    def test_is_publishable_rights_restricted(self):
        from sfc.video_intelligence.ingestion.models import VideoMetadata
        meta = VideoMetadata(rights_status=RightsStatus.RESTRICTED)
        assert meta.is_publishable_rights is False

    def test_duration_label_minutes(self):
        from sfc.video_intelligence.ingestion.models import VideoMetadata
        meta = VideoMetadata(duration_seconds=125.0)
        assert "2:" in meta.duration_label

    @pytest.mark.asyncio
    async def test_processing_log_populated(self):
        svc = _svc()
        with patch.dict(os.environ, {"VIDEO_PROCESSING_ENABLED": "false"}):
            result = await svc.ingest(_source())
        assert len(result.processing_log) >= 1
