"""Tests for Sport Event Detection Layer."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from sfc.video_intelligence.event_detection.models import SportEvent, SportEventType
from sfc.video_intelligence.event_detection.service import SportEventDetectionService
from sfc.video_intelligence.understanding.models import (
    TranscriptSegment,
    VideoTranscript,
    VideoUnderstandingResult,
)


def _understanding_with_text(video_id: str, text: str) -> VideoUnderstandingResult:
    transcript = VideoTranscript(
        video_id=video_id,
        segments=[
            TranscriptSegment(start_seconds=45.0, end_seconds=60.0, text=text)
        ],
        full_text=text,
    )
    return VideoUnderstandingResult(
        video_id=video_id,
        transcript=transcript,
    )


def _empty_understanding(video_id: str = "vid-1") -> VideoUnderstandingResult:
    return VideoUnderstandingResult(
        video_id=video_id,
        transcript=VideoTranscript(video_id=video_id),
    )


class TestEventDetectionDryRun:
    @pytest.mark.asyncio
    async def test_dry_run_returns_events(self):
        svc = SportEventDetectionService()
        with patch.dict(os.environ, {"VIDEO_PROCESSING_ENABLED": "false"}):
            result = await svc.detect(_empty_understanding())
        assert result.dry_run is True
        assert result.total_events > 0

    @pytest.mark.asyncio
    async def test_dry_run_includes_goal_event(self):
        svc = SportEventDetectionService()
        with patch.dict(os.environ, {"VIDEO_PROCESSING_ENABLED": "false"}):
            result = await svc.detect(_empty_understanding())
        event_types = [e.event_type for e in result.events]
        assert SportEventType.GOAL in event_types


class TestKeywordDetection:
    @pytest.mark.asyncio
    async def test_detects_goal_keyword_arabic(self):
        svc = SportEventDetectionService()
        understanding = _understanding_with_text("vid-1", "سجل الفريق هدف رائع")
        with patch.dict(os.environ, {"VIDEO_PROCESSING_ENABLED": "true"}):
            result = await svc.detect(understanding)
        event_types = [e.event_type for e in result.events]
        assert SportEventType.GOAL in event_types

    @pytest.mark.asyncio
    async def test_detects_goal_keyword_english(self):
        svc = SportEventDetectionService()
        understanding = _understanding_with_text("vid-1", "He scored an amazing goal!")
        with patch.dict(os.environ, {"VIDEO_PROCESSING_ENABLED": "true"}):
            result = await svc.detect(understanding)
        event_types = [e.event_type for e in result.events]
        assert SportEventType.GOAL in event_types

    @pytest.mark.asyncio
    async def test_detects_save_keyword(self):
        svc = SportEventDetectionService()
        understanding = _understanding_with_text("vid-1", "The goalkeeper made an incredible save")
        with patch.dict(os.environ, {"VIDEO_PROCESSING_ENABLED": "true"}):
            result = await svc.detect(understanding)
        event_types = [e.event_type for e in result.events]
        assert SportEventType.SAVE in event_types

    @pytest.mark.asyncio
    async def test_detects_penalty_keyword(self):
        svc = SportEventDetectionService()
        understanding = _understanding_with_text("vid-1", "Penalty kick awarded")
        with patch.dict(os.environ, {"VIDEO_PROCESSING_ENABLED": "true"}):
            result = await svc.detect(understanding)
        event_types = [e.event_type for e in result.events]
        assert SportEventType.PENALTY in event_types

    @pytest.mark.asyncio
    async def test_no_events_from_empty_transcript(self):
        svc = SportEventDetectionService()
        with patch.dict(os.environ, {"VIDEO_PROCESSING_ENABLED": "true"}):
            result = await svc.detect(_empty_understanding())
        assert result.total_events == 0

    @pytest.mark.asyncio
    async def test_deduplication_prevents_duplicate_events(self):
        svc = SportEventDetectionService()
        # Two segments saying "goal" within 3 seconds of each other
        transcript = VideoTranscript(
            video_id="vid-1",
            segments=[
                TranscriptSegment(start_seconds=45.0, end_seconds=47.0, text="goal scored!"),
                TranscriptSegment(start_seconds=46.0, end_seconds=48.0, text="what a goal!"),
            ],
            full_text="goal scored! what a goal!",
        )
        understanding = VideoUnderstandingResult(video_id="vid-1", transcript=transcript)
        with patch.dict(os.environ, {"VIDEO_PROCESSING_ENABLED": "true"}):
            result = await svc.detect(understanding)
        goal_events = [e for e in result.events if e.event_type == SportEventType.GOAL]
        assert len(goal_events) == 1


class TestHighlightScoring:
    def test_goal_has_high_highlight_score(self):
        svc = SportEventDetectionService()
        event = SportEvent(
            video_id="vid-1",
            event_type=SportEventType.GOAL,
            start_seconds=0.0,
            end_seconds=20.0,
            confidence=0.95,
        )
        score = svc._compute_highlight_score(event)
        assert score >= 85.0

    def test_corner_has_lower_score_than_goal(self):
        svc = SportEventDetectionService()
        goal_event = SportEvent(
            video_id="vid-1",
            event_type=SportEventType.GOAL,
            start_seconds=0.0,
            end_seconds=20.0,
            confidence=0.90,
        )
        corner_event = SportEvent(
            video_id="vid-1",
            event_type=SportEventType.CORNER,
            start_seconds=0.0,
            end_seconds=20.0,
            confidence=0.90,
        )
        assert svc._compute_highlight_score(goal_event) > svc._compute_highlight_score(corner_event)

    def test_top_events_sorted_by_score(self):
        from sfc.video_intelligence.event_detection.models import EventDetectionResult
        result = EventDetectionResult(video_id="vid-1")
        result.events = [
            SportEvent(video_id="vid-1", event_type=SportEventType.CORNER,
                       start_seconds=0, end_seconds=5, highlight_score=40.0),
            SportEvent(video_id="vid-1", event_type=SportEventType.GOAL,
                       start_seconds=10, end_seconds=30, highlight_score=92.0),
            SportEvent(video_id="vid-1", event_type=SportEventType.SAVE,
                       start_seconds=40, end_seconds=50, highlight_score=80.0),
        ]
        top = result.top_events(n=2)
        assert top[0].event_type == SportEventType.GOAL
        assert top[1].event_type == SportEventType.SAVE

    def test_event_clip_bounds(self):
        event = SportEvent(
            video_id="vid-1",
            event_type=SportEventType.GOAL,
            start_seconds=45.0,
            end_seconds=50.0,
        )
        assert event.clip_start == 40.0  # 5s pre-roll
        assert event.clip_end == 60.0   # 10s post-roll
