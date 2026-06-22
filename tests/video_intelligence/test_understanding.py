"""Tests for Video Understanding Layer."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from sfc.video_intelligence.ingestion.models import (
    RightsStatus,
    VideoIngestionResult,
    VideoMetadata,
    VideoProcessingStatus,
    VideoSource,
    VideoSourceType,
)
from sfc.video_intelligence.understanding.models import (
    TranscriptSegment,
    VideoTranscript,
    VideoUnderstandingResult,
)
from sfc.video_intelligence.understanding.service import VideoUnderstandingService


def _make_ingestion(title: str = "Test", path: str = "") -> VideoIngestionResult:
    source = VideoSource(
        source_type=VideoSourceType.MATCH_RECORDING,
        title=title,
        rights_status=RightsStatus.OWNED,
        path=path,
    )
    meta = VideoMetadata(title=title, duration_seconds=120.0)
    return VideoIngestionResult(
        source=source,
        status=VideoProcessingStatus.DRY_RUN,
        video_metadata=meta,
    )


class TestVideoUnderstandingDryRun:
    @pytest.mark.asyncio
    async def test_dry_run_returns_result(self):
        svc = VideoUnderstandingService()
        ingestion = _make_ingestion("Match Highlights")
        with patch.dict(os.environ, {"VIDEO_PROCESSING_ENABLED": "false"}):
            result = await svc.analyze(ingestion)
        assert result.dry_run is True
        assert result.video_id is not None

    @pytest.mark.asyncio
    async def test_dry_run_has_placeholder_transcript(self):
        svc = VideoUnderstandingService()
        ingestion = _make_ingestion("Goal Fest")
        with patch.dict(os.environ, {"VIDEO_PROCESSING_ENABLED": "false"}):
            result = await svc.analyze(ingestion)
        assert result.has_transcript is True
        assert "[DRY RUN]" in result.transcript.full_text

    @pytest.mark.asyncio
    async def test_dry_run_has_scenes(self):
        svc = VideoUnderstandingService()
        with patch.dict(os.environ, {"VIDEO_PROCESSING_ENABLED": "false"}):
            result = await svc.analyze(_make_ingestion())
        assert len(result.scenes) >= 1

    @pytest.mark.asyncio
    async def test_dry_run_has_summary(self):
        svc = VideoUnderstandingService()
        with patch.dict(os.environ, {"VIDEO_PROCESSING_ENABLED": "false"}):
            result = await svc.analyze(_make_ingestion())
        assert result.summary != ""


class TestTranscriptModel:
    def test_segments_in_range(self):
        transcript = VideoTranscript(
            video_id="vid-1",
            segments=[
                TranscriptSegment(start_seconds=0, end_seconds=10, text="Hello"),
                TranscriptSegment(start_seconds=10, end_seconds=20, text="World"),
                TranscriptSegment(start_seconds=20, end_seconds=30, text="Goal"),
            ],
            full_text="Hello World Goal",
        )
        segs = transcript.segments_in_range(5, 25)
        assert len(segs) == 3

    def test_segments_in_range_no_overlap(self):
        transcript = VideoTranscript(
            video_id="vid-1",
            segments=[
                TranscriptSegment(start_seconds=50, end_seconds=60, text="Late"),
            ],
            full_text="Late",
        )
        segs = transcript.segments_in_range(0, 10)
        assert segs == []

    def test_text_in_range_joins_segments(self):
        transcript = VideoTranscript(
            video_id="vid-1",
            segments=[
                TranscriptSegment(start_seconds=0, end_seconds=5, text="الهدف"),
                TranscriptSegment(start_seconds=5, end_seconds=10, text="الأول"),
            ],
            full_text="الهدف الأول",
        )
        text = transcript.text_in_range(0, 10)
        assert "الهدف" in text
        assert "الأول" in text

    def test_duration_covered(self):
        transcript = VideoTranscript(
            video_id="vid-1",
            segments=[
                TranscriptSegment(start_seconds=0, end_seconds=30, text="..."),
            ],
            full_text="...",
        )
        assert transcript.duration_covered == 30.0

    def test_duration_covered_empty(self):
        transcript = VideoTranscript(video_id="vid-1")
        assert transcript.duration_covered == 0.0
