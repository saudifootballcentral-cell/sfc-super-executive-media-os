"""Video Intelligence Orchestrator — drives the full 12-stage pipeline."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from sfc.video_intelligence.captioning.models import CaptioningResult
from sfc.video_intelligence.clipping.models import VideoClip
from sfc.video_intelligence.event_detection.models import EventDetectionResult
from sfc.video_intelligence.enhancement.models import EnhancementResult
from sfc.video_intelligence.governance.models import ClipGovernanceResult
from sfc.video_intelligence.ingestion.models import VideoIngestionResult, VideoSource
from sfc.video_intelligence.interview_detection.models import InterviewDetectionResult
from sfc.video_intelligence.learning.models import ClipPerformanceRecord
from sfc.video_intelligence.packaging.models import ClipPackage
from sfc.video_intelligence.rendering.models import RenderedVideo
from sfc.video_intelligence.scoring.models import ClipScore
from sfc.video_intelligence.understanding.models import VideoUnderstandingResult

logger = logging.getLogger("sfc.video_intelligence.orchestrator")


@dataclass
class ClipPipelineResult:
    """Result for a single clip through the full pipeline."""
    clip: VideoClip
    score: ClipScore
    enhancement: EnhancementResult
    captioning: CaptioningResult
    rendering: RenderedVideo | None
    package: ClipPackage
    governance: ClipGovernanceResult
    publish_record: dict
    learning_record: ClipPerformanceRecord | None = None


@dataclass
class VideoIntelligenceResult:
    """Full result of the Video Intelligence pipeline for one video."""
    run_id: str = field(default_factory=lambda: str(uuid4()))
    ingestion: VideoIngestionResult | None = None
    understanding: VideoUnderstandingResult | None = None
    events: EventDetectionResult | None = None
    interviews: InterviewDetectionResult | None = None
    clip_results: list[ClipPipelineResult] = field(default_factory=list)
    total_clips_extracted: int = 0
    total_clips_published: int = 0
    pipeline_errors: list[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def succeeded(self) -> bool:
        return self.ingestion is not None and self.ingestion.succeeded

    @property
    def duration_seconds(self) -> float:
        if self.completed_at is None:
            return 0.0
        return (self.completed_at - self.started_at).total_seconds()

    def summary(self) -> str:
        status = "OK" if self.succeeded else "FAILED"
        return (
            f"[VideoIntelligence] run_id={self.run_id} "
            f"status={status} clips={self.total_clips_extracted} "
            f"published={self.total_clips_published} "
            f"duration={self.duration_seconds:.1f}s"
        )


_singleton: "VideoIntelligenceOrchestrator | None" = None


def get_video_intelligence_orchestrator() -> "VideoIntelligenceOrchestrator":
    global _singleton
    if _singleton is None:
        _singleton = VideoIntelligenceOrchestrator()
    return _singleton


class VideoIntelligenceOrchestrator:
    """Orchestrates all 12 Video Intelligence pipeline stages."""

    def __init__(self) -> None:
        # Import here to allow service-level mocking in tests
        from sfc.video_intelligence.ingestion.service import get_video_ingestion_service
        from sfc.video_intelligence.understanding.service import get_video_understanding_service
        from sfc.video_intelligence.event_detection.service import get_sport_event_detection_service
        from sfc.video_intelligence.interview_detection.service import get_interview_detection_service
        from sfc.video_intelligence.clipping.service import get_smart_clipping_engine
        from sfc.video_intelligence.scoring.service import get_clip_scoring_engine
        from sfc.video_intelligence.enhancement.service import get_clip_enhancement_engine
        from sfc.video_intelligence.captioning.service import get_auto_captioning_engine
        from sfc.video_intelligence.rendering.service import get_video_rendering_service
        from sfc.video_intelligence.packaging.service import get_clip_packaging_engine
        from sfc.video_intelligence.governance.service import get_clip_governance_layer
        from sfc.video_intelligence.publishing.service import get_clip_publishing_integration
        from sfc.video_intelligence.learning.service import get_clip_learning_loop

        from sfc.video_intelligence.voiceover.service import get_voiceover_service
        from sfc.video_intelligence.music.service import get_music_library_service

        self._ingestion = get_video_ingestion_service()
        self._understanding = get_video_understanding_service()
        self._event_detection = get_sport_event_detection_service()
        self._interview_detection = get_interview_detection_service()
        self._clipping = get_smart_clipping_engine()
        self._scoring = get_clip_scoring_engine()
        self._enhancement = get_clip_enhancement_engine()
        self._captioning = get_auto_captioning_engine()
        self._voiceover = get_voiceover_service()
        self._music = get_music_library_service()
        self._rendering = get_video_rendering_service()
        self._packaging = get_clip_packaging_engine()
        self._governance = get_clip_governance_layer()
        self._publishing = get_clip_publishing_integration()
        self._learning = get_clip_learning_loop()

    async def process_video(
        self,
        source: VideoSource,
        run_id: str | None = None,
    ) -> VideoIntelligenceResult:
        result = VideoIntelligenceResult(
            run_id=run_id or str(uuid4()),
        )
        logger.info(
            "[Orchestrator] Starting pipeline run_id=%s source=%s",
            result.run_id,
            source.source_type.value,
        )

        # ── Stage 1: Ingestion ──────────────────────────────────────────────
        try:
            ingestion = await self._ingestion.ingest(source, run_id=result.run_id)
            result.ingestion = ingestion
            if not ingestion.succeeded:
                result.pipeline_errors.append(
                    f"Ingestion failed: {ingestion.status.value} — {ingestion.error_message}"
                )
                result.completed_at = datetime.utcnow()
                return result
        except Exception as exc:
            result.pipeline_errors.append(f"Ingestion exception: {exc}")
            result.completed_at = datetime.utcnow()
            return result

        # ── Stage 2: Understanding ──────────────────────────────────────────
        try:
            understanding = await self._understanding.analyze(ingestion)
            result.understanding = understanding
        except Exception as exc:
            result.pipeline_errors.append(f"Understanding exception: {exc}")
            understanding = None

        if understanding is None:
            result.completed_at = datetime.utcnow()
            return result

        # ── Stage 3: Sport Event Detection ─────────────────────────────────
        try:
            events = await self._event_detection.detect(understanding)
            result.events = events
        except Exception as exc:
            result.pipeline_errors.append(f"EventDetection exception: {exc}")
            from sfc.video_intelligence.event_detection.models import EventDetectionResult
            events = EventDetectionResult(video_id=understanding.video_id)

        # ── Stage 4: Interview / Press Conference Detection ─────────────────
        try:
            interviews = await self._interview_detection.detect(understanding, ingestion)
            result.interviews = interviews
        except Exception as exc:
            result.pipeline_errors.append(f"InterviewDetection exception: {exc}")
            from sfc.video_intelligence.interview_detection.models import InterviewDetectionResult
            interviews = InterviewDetectionResult(video_id=understanding.video_id)

        # ── Stage 5: Smart Clipping ─────────────────────────────────────────
        try:
            clips = await self._clipping.extract_clips(ingestion, events, interviews)
        except Exception as exc:
            result.pipeline_errors.append(f"Clipping exception: {exc}")
            clips = []

        result.total_clips_extracted = len(clips)

        # ── Stages 6–12: Per-clip pipeline ─────────────────────────────────
        rights_status = (
            ingestion.video_metadata.rights_status
            if ingestion.video_metadata
            else source.rights_status
        )
        transcript = understanding.transcript if understanding else None

        for clip in clips:
            clip_result = await self._process_clip(clip, transcript, rights_status, source)
            result.clip_results.append(clip_result)
            if clip_result.publish_record.get("status") in ("submitted", "blocked"):
                if clip_result.package.published:
                    result.total_clips_published += 1

        result.completed_at = datetime.utcnow()
        logger.info(result.summary())
        return result

    async def _process_clip(
        self,
        clip: VideoClip,
        transcript: Any,
        rights_status: Any,
        source: "VideoSource | None" = None,
    ) -> ClipPipelineResult:
        # Stage 6: Score
        try:
            score = await self._scoring.score(clip)
        except Exception as exc:
            logger.error("[Orchestrator] Scoring error clip=%s: %s", clip.clip_id, exc)
            from sfc.video_intelligence.scoring.models import ClipScore
            score = ClipScore(clip_id=clip.clip_id, overall_score=0.0)

        # Stage 7: Enhance
        try:
            enhancement = await self._enhancement.enhance(clip, score)
        except Exception as exc:
            logger.error("[Orchestrator] Enhancement error clip=%s: %s", clip.clip_id, exc)
            enhancement = EnhancementResult(clip_id=clip.clip_id)

        # Stage 8: Caption
        try:
            captioning = await self._captioning.caption(clip, transcript)
        except Exception as exc:
            logger.error("[Orchestrator] Captioning error clip=%s: %s", clip.clip_id, exc)
            captioning = CaptioningResult(clip_id=clip.clip_id)

        # Stage 8.1: Voice-over synthesis — generates Arabic narration from clip description
        voiceover_track = None
        try:
            vo_text = clip.description or clip.title
            voiceover_track = await self._voiceover.synthesise(clip.clip_id, vo_text)
        except Exception as exc:
            logger.debug("[Orchestrator] Voiceover skipped clip=%s: %s", clip.clip_id, exc)

        # Stage 8.2: Background music selection — theme-matched from local library
        music_track = None
        try:
            music_track = self._music.select(clip.clip_type)
        except Exception as exc:
            logger.debug("[Orchestrator] Music skipped clip=%s: %s", clip.clip_id, exc)

        # Stage 8.5: Render — brand, subtitle, audio mix each enhanced variant
        rendering: RenderedVideo | None = None
        try:
            best_variant = (
                enhancement.ready_variants[0] if enhancement.ready_variants else None
            )
            if best_variant:
                audio_tracks = [
                    t for t in [voiceover_track, music_track] if t is not None
                ]
                rendering = await self._rendering.render_clip(
                    clip=clip,
                    variant=best_variant,
                    captioning=captioning,
                    audio_tracks=audio_tracks if audio_tracks else None,
                )
                if rendering.is_ready:
                    best_variant.local_path = rendering.local_path
        except Exception as exc:
            logger.error("[Orchestrator] Rendering error clip=%s: %s", clip.clip_id, exc)

        # Stage 9: Package — propagate attribution + platform rights from source
        try:
            package = await self._packaging.package(
                clip, score, enhancement, captioning, source=source
            )
        except Exception as exc:
            logger.error("[Orchestrator] Packaging error clip=%s: %s", clip.clip_id, exc)
            from sfc.video_intelligence.packaging.models import ClipPackage
            package = ClipPackage(
                clip_id=clip.clip_id,
                video_id=clip.video_id,
                title=clip.title,
            )

        # Stage 10: Governance — checks rights, expiry, brand safety, quality
        try:
            governance = await self._governance.review(package, rights_status, source=source)
        except Exception as exc:
            logger.error("[Orchestrator] Governance error clip=%s: %s", clip.clip_id, exc)
            governance = ClipGovernanceResult(
                clip_id=clip.clip_id,
                package_id=package.package_id,
            )
        package.governance_cleared = governance.cleared_for_publishing

        # Stage 11: Publish
        try:
            publish_record = await self._publishing.publish(package, governance)
        except Exception as exc:
            logger.error("[Orchestrator] Publishing error clip=%s: %s", clip.clip_id, exc)
            publish_record = {"status": "error", "reason": str(exc)}

        # Stage 12: Learning — record prediction for later feedback
        try:
            learning_record = self._learning.record_prediction(package, score)
        except Exception as exc:
            logger.debug("[Orchestrator] Learning record error: %s", exc)
            learning_record = None

        return ClipPipelineResult(
            clip=clip,
            score=score,
            enhancement=enhancement,
            captioning=captioning,
            rendering=rendering,
            package=package,
            governance=governance,
            publish_record=publish_record,
            learning_record=learning_record,
        )
