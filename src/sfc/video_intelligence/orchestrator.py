"""Video Intelligence Orchestrator — drives the full 12-stage pipeline.

Supports three production modes:
  Mode A — process_video()     — real footage ingestion pipeline
  Mode B — process_ai_video()  — AI-generated script → storyboard → video pipeline
  Mode C — process_hybrid()    — mix real footage + AI-generated gap fill
"""

from __future__ import annotations

import logging
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
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

        from sfc.video_intelligence.script.service import get_script_generation_service
        from sfc.video_intelligence.storyboard.service import get_storyboard_generation_service
        from sfc.video_intelligence.ai_video.service import get_ai_video_generation_service
        from sfc.video_intelligence.router.service import get_video_production_router

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
        self._script = get_script_generation_service()
        self._storyboard = get_storyboard_generation_service()
        self._ai_video = get_ai_video_generation_service()
        self._router = get_video_production_router()

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
                    best_variant.public_url = rendering.public_url
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

    # ──────────────────────────────────────────────────────────────────────────
    # Mode B — AI Video Production
    # ──────────────────────────────────────────────────────────────────────────

    async def process_ai_video(
        self,
        topic: str,
        platforms: list[str] | None = None,
        duration_secs: float = 60.0,
        style: str = "sports_highlight",
        run_id: str | None = None,
    ) -> "VideoIntelligenceResult":
        """Mode B: script → storyboard → AI video → voice-over → music → render → publish."""
        platforms = platforms or ["youtube_video", "youtube_short"]
        result = VideoIntelligenceResult(run_id=run_id or str(uuid4()))
        result.metadata["mode"] = "ai_video"
        result.metadata["topic"] = topic

        logger.info(
            "[Orchestrator:ModeB] Starting AI video run_id=%s topic=%s platforms=%s",
            result.run_id, topic, platforms,
        )

        # Stage B1: Generate script with Claude
        try:
            script = await self._script.generate(
                topic=topic,
                duration_secs=duration_secs,
                style=style,
            )
            result.metadata["script_id"] = script.script_id
            logger.info("[Orchestrator:ModeB] Script generated scenes=%d", script.scene_count)
        except Exception as exc:
            result.pipeline_errors.append(f"Script generation failed: {exc}")
            result.completed_at = datetime.utcnow()
            return result

        # Stage B2: Build storyboard for each platform
        for platform in platforms:
            try:
                storyboard = await self._storyboard.create(script, platform=platform)

                # Stage B3: Generate AI video scenes (parallel per scene)
                ai_results = await self._ai_video.generate_video(storyboard)

                # Build synthetic VideoClips from AI results
                clips = self._build_ai_clips(topic, script, storyboard, ai_results, platform)
                result.total_clips_extracted += len(clips)

                # Stage B4–B12: Per-clip pipeline (same as Mode A from scoring onwards)
                for clip in clips:
                    clip_result = await self._process_clip(
                        clip, transcript=None, rights_status=None, source=None
                    )
                    result.clip_results.append(clip_result)
                    if clip_result.package.published:
                        result.total_clips_published += 1

            except Exception as exc:
                logger.error(
                    "[Orchestrator:ModeB] Platform %s failed: %s", platform, exc
                )
                result.pipeline_errors.append(f"Platform {platform} failed: {exc}")

        result.completed_at = datetime.utcnow()
        logger.info(
            "[Orchestrator:ModeB] Completed run_id=%s clips=%d published=%d",
            result.run_id, result.total_clips_extracted, result.total_clips_published,
        )
        return result

    def _build_ai_clips(
        self,
        topic: str,
        script,
        storyboard,
        ai_results: list,
        platform: str,
    ) -> list[VideoClip]:
        """Convert AI video results into synthetic VideoClips for the existing pipeline."""
        from sfc.video_intelligence.clipping.models import ClipSourceType

        script_lookup = {s.scene_id: s for s in script.scenes}
        clips: list[VideoClip] = []
        cumulative_start = 0.0

        for sb_scene, ai_result in zip(storyboard.scenes, ai_results):
            original_scene = script_lookup.get(sb_scene.script_scene_id)
            narration = original_scene.narration if original_scene else topic

            duration = sb_scene.duration_seconds

            clip = VideoClip(
                video_id=storyboard.storyboard_id,
                title=original_scene.title if original_scene else topic,
                description=narration,
                start_seconds=cumulative_start,
                end_seconds=cumulative_start + duration,
                duration_seconds=duration,
                clip_type=platform,
                source_type=ClipSourceType.HIGHLIGHT,
                local_path=ai_result.local_path,
                metadata={
                    "ai_video": True,
                    "provider": ai_result.provider,
                    "public_url": ai_result.public_url,
                    "scene_id": sb_scene.scene_id,
                    "script_id": script.script_id,
                    "storyboard_id": storyboard.storyboard_id,
                },
            )
            cumulative_start += duration
            clips.append(clip)

        return clips

    # ──────────────────────────────────────────────────────────────────────────
    # Mode C — Hybrid Production
    # ──────────────────────────────────────────────────────────────────────────

    async def process_hybrid(
        self,
        source: "VideoSource",
        topic: str,
        platforms: list[str] | None = None,
        run_id: str | None = None,
    ) -> "VideoIntelligenceResult":
        """Mode C: ingest real footage → find gaps → fill with AI scenes → publish."""
        platforms = platforms or ["youtube_video", "youtube_short"]
        result = VideoIntelligenceResult(run_id=run_id or str(uuid4()))
        result.metadata["mode"] = "hybrid"
        result.metadata["topic"] = topic

        logger.info(
            "[Orchestrator:ModeC] Starting hybrid run_id=%s source=%s topic=%s",
            result.run_id, source.source_type.value, topic,
        )

        # Stage C1: Run Mode A pipeline for real footage
        real_result = await self.process_video(source, run_id=f"{result.run_id}_real")
        result.ingestion = real_result.ingestion
        result.understanding = real_result.understanding
        result.events = real_result.events
        result.interviews = real_result.interviews
        result.pipeline_errors.extend(real_result.pipeline_errors)

        real_clips = real_result.clip_results
        result.total_clips_extracted += real_result.total_clips_extracted
        result.total_clips_published += real_result.total_clips_published
        result.clip_results.extend(real_clips)

        logger.info(
            "[Orchestrator:ModeC] Real footage done — clips=%d published=%d",
            real_result.total_clips_extracted, real_result.total_clips_published,
        )

        # Stage C2: Determine coverage gaps in timeline
        total_duration = (
            real_result.ingestion.video_metadata.duration_seconds
            if real_result.ingestion and real_result.ingestion.video_metadata
            else 0.0
        )
        gaps = self._find_timeline_gaps(real_clips, total_duration)

        if not gaps:
            logger.info("[Orchestrator:ModeC] No timeline gaps — no AI fill needed")
            result.completed_at = datetime.utcnow()
            result.metadata["ai_scenes_generated"] = 0
            return result

        logger.info("[Orchestrator:ModeC] Found %d timeline gaps — generating AI fill", len(gaps))

        # Stage C3: Generate AI scenes for gaps
        gap_duration = sum(g[1] - g[0] for g in gaps)
        ai_topic = f"{topic} — additional coverage"
        ai_num_scenes = max(1, len(gaps))

        try:
            script = await self._script.generate(
                topic=ai_topic,
                duration_secs=gap_duration,
                style="sports_highlight",
                num_scenes=ai_num_scenes,
            )

            for platform in platforms:
                storyboard = await self._storyboard.create(script, platform=platform)
                ai_results = await self._ai_video.generate_video(storyboard)
                ai_clips = self._build_ai_clips(ai_topic, script, storyboard, ai_results, platform)

                result.total_clips_extracted += len(ai_clips)
                result.metadata["ai_scenes_generated"] = len(ai_clips)

                for clip in ai_clips:
                    clip_result = await self._process_clip(
                        clip, transcript=None, rights_status=None, source=None
                    )
                    result.clip_results.append(clip_result)
                    if clip_result.package.published:
                        result.total_clips_published += 1

        except Exception as exc:
            logger.error("[Orchestrator:ModeC] AI gap fill failed: %s", exc)
            result.pipeline_errors.append(f"AI gap fill failed: {exc}")

        result.completed_at = datetime.utcnow()
        logger.info(
            "[Orchestrator:ModeC] Completed run_id=%s clips=%d published=%d",
            result.run_id, result.total_clips_extracted, result.total_clips_published,
        )
        return result

    def _find_timeline_gaps(
        self,
        clip_results: list["ClipPipelineResult"],
        total_duration: float,
        min_gap_seconds: float = 30.0,
    ) -> list[tuple[float, float]]:
        """Return (start, end) pairs for uncovered intervals in the timeline."""
        if not clip_results or total_duration <= 0:
            if total_duration > 0:
                return [(0.0, min(total_duration, 60.0))]
            return []

        covered: list[tuple[float, float]] = sorted(
            (cr.clip.start_seconds, cr.clip.end_seconds)
            for cr in clip_results
        )

        gaps: list[tuple[float, float]] = []
        cursor = 0.0
        for start, end in covered:
            if start - cursor >= min_gap_seconds:
                gaps.append((cursor, start))
            cursor = max(cursor, end)

        if total_duration - cursor >= min_gap_seconds:
            gaps.append((cursor, total_duration))

        return gaps
