"""Tests for Video Intelligence Orchestrator (full pipeline)."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from sfc.video_intelligence.ingestion.models import (
    RightsStatus,
    VideoSource,
    VideoSourceType,
)
from sfc.video_intelligence.orchestrator import VideoIntelligenceOrchestrator


def _source(
    source_type: VideoSourceType = VideoSourceType.MATCH_RECORDING,
    rights: RightsStatus = RightsStatus.OWNED,
    title: str = "SFC Match",
    path: str = "",
) -> VideoSource:
    return VideoSource(
        source_type=source_type,
        title=title,
        rights_status=rights,
        path=path,
    )


class TestOrchestratorDryRun:
    @pytest.mark.asyncio
    async def test_full_pipeline_dry_run_succeeds(self):
        orch = VideoIntelligenceOrchestrator()
        with patch.dict(os.environ, {"VIDEO_PROCESSING_ENABLED": "false"}):
            result = await orch.process_video(_source())
        assert result.succeeded is True

    @pytest.mark.asyncio
    async def test_dry_run_extracts_clips(self):
        orch = VideoIntelligenceOrchestrator()
        with patch.dict(os.environ, {"VIDEO_PROCESSING_ENABLED": "false"}):
            result = await orch.process_video(_source())
        assert result.total_clips_extracted > 0

    @pytest.mark.asyncio
    async def test_dry_run_produces_clip_results(self):
        orch = VideoIntelligenceOrchestrator()
        with patch.dict(os.environ, {"VIDEO_PROCESSING_ENABLED": "false"}):
            result = await orch.process_video(_source())
        assert len(result.clip_results) > 0

    @pytest.mark.asyncio
    async def test_dry_run_all_stages_populated(self):
        orch = VideoIntelligenceOrchestrator()
        with patch.dict(os.environ, {"VIDEO_PROCESSING_ENABLED": "false"}):
            result = await orch.process_video(_source())
        assert result.ingestion is not None
        assert result.understanding is not None
        assert result.events is not None
        assert result.interviews is not None

    @pytest.mark.asyncio
    async def test_dry_run_clip_results_have_scores(self):
        orch = VideoIntelligenceOrchestrator()
        with patch.dict(os.environ, {"VIDEO_PROCESSING_ENABLED": "false"}):
            result = await orch.process_video(_source())
        for cr in result.clip_results:
            assert cr.score.overall_score > 0
            assert cr.score.brand_alignment > 0

    @pytest.mark.asyncio
    async def test_dry_run_clip_results_have_packages(self):
        orch = VideoIntelligenceOrchestrator()
        with patch.dict(os.environ, {"VIDEO_PROCESSING_ENABLED": "false"}):
            result = await orch.process_video(_source())
        for cr in result.clip_results:
            assert cr.package is not None
            assert cr.package.title != ""

    @pytest.mark.asyncio
    async def test_dry_run_clip_results_have_governance(self):
        orch = VideoIntelligenceOrchestrator()
        with patch.dict(os.environ, {"VIDEO_PROCESSING_ENABLED": "false"}):
            result = await orch.process_video(_source())
        for cr in result.clip_results:
            assert cr.governance is not None
            assert cr.governance.status is not None

    @pytest.mark.asyncio
    async def test_dry_run_captioning_tracks_present(self):
        orch = VideoIntelligenceOrchestrator()
        with patch.dict(os.environ, {"VIDEO_PROCESSING_ENABLED": "false"}):
            result = await orch.process_video(_source())
        for cr in result.clip_results:
            assert cr.captioning is not None

    @pytest.mark.asyncio
    async def test_dry_run_summary_not_empty(self):
        orch = VideoIntelligenceOrchestrator()
        with patch.dict(os.environ, {"VIDEO_PROCESSING_ENABLED": "false"}):
            result = await orch.process_video(_source())
        assert result.summary() != ""
        assert result.run_id in result.summary()


class TestOrchestratorRightsBlocking:
    @pytest.mark.asyncio
    async def test_restricted_source_fails_early(self):
        orch = VideoIntelligenceOrchestrator()
        result = await orch.process_video(_source(rights=RightsStatus.RESTRICTED))
        assert result.succeeded is False
        assert result.total_clips_extracted == 0
        assert len(result.pipeline_errors) > 0

    @pytest.mark.asyncio
    async def test_restricted_source_has_no_clips(self):
        orch = VideoIntelligenceOrchestrator()
        result = await orch.process_video(_source(rights=RightsStatus.RESTRICTED))
        assert result.clip_results == []

    @pytest.mark.asyncio
    async def test_unknown_rights_clips_not_cleared_for_publishing(self):
        orch = VideoIntelligenceOrchestrator()
        with patch.dict(os.environ, {"VIDEO_PROCESSING_ENABLED": "false"}):
            result = await orch.process_video(_source(rights=RightsStatus.UNKNOWN))
        # Should succeed but governance should block publishing
        if result.clip_results:
            for cr in result.clip_results:
                assert cr.governance.cleared_for_publishing is False


class TestOrchestratorSourceTypes:
    @pytest.mark.asyncio
    async def test_press_conference_pipeline(self):
        orch = VideoIntelligenceOrchestrator()
        with patch.dict(os.environ, {"VIDEO_PROCESSING_ENABLED": "false"}):
            result = await orch.process_video(
                _source(
                    source_type=VideoSourceType.PRESS_CONFERENCE,
                    title="Post-Match Press Conference",
                )
            )
        assert result.succeeded is True

    @pytest.mark.asyncio
    async def test_interview_pipeline(self):
        orch = VideoIntelligenceOrchestrator()
        with patch.dict(os.environ, {"VIDEO_PROCESSING_ENABLED": "false"}):
            result = await orch.process_video(
                _source(
                    source_type=VideoSourceType.INTERVIEW,
                    title="Player Interview",
                )
            )
        assert result.succeeded is True

    @pytest.mark.asyncio
    async def test_training_video_pipeline(self):
        orch = VideoIntelligenceOrchestrator()
        with patch.dict(os.environ, {"VIDEO_PROCESSING_ENABLED": "false"}):
            result = await orch.process_video(
                _source(
                    source_type=VideoSourceType.TRAINING_VIDEO,
                    title="Training Session",
                )
            )
        assert result.succeeded is True


class TestOrchestratorLearning:
    @pytest.mark.asyncio
    async def test_learning_records_created(self):
        orch = VideoIntelligenceOrchestrator()
        with patch.dict(os.environ, {"VIDEO_PROCESSING_ENABLED": "false"}):
            result = await orch.process_video(_source())
        for cr in result.clip_results:
            assert cr.learning_record is not None

    @pytest.mark.asyncio
    async def test_run_id_propagated(self):
        orch = VideoIntelligenceOrchestrator()
        with patch.dict(os.environ, {"VIDEO_PROCESSING_ENABLED": "false"}):
            result = await orch.process_video(_source(), run_id="test-run-123")
        assert result.run_id == "test-run-123"
