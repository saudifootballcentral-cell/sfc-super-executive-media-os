"""Video Understanding Service — transcription, scene detection, frame indexing."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any
from uuid import uuid4

from sfc.video_intelligence.ingestion.models import VideoFrameIndex, VideoIngestionResult
from sfc.video_intelligence.shared.constants import (
    FRAME_SAMPLE_RATE,
    WHISPER_API_KEY,
    is_video_processing_enabled,
)
from sfc.video_intelligence.understanding.models import (
    SceneSegment,
    TranscriptSegment,
    VideoTranscript,
    VideoUnderstandingResult,
)

logger = logging.getLogger("sfc.video_intelligence.understanding")

_singleton: "VideoUnderstandingService | None" = None


def get_video_understanding_service() -> "VideoUnderstandingService":
    global _singleton
    if _singleton is None:
        _singleton = VideoUnderstandingService()
    return _singleton


class VideoUnderstandingService:
    """Transcribes audio, detects scenes, and indexes frames."""

    def __init__(self) -> None:
        self._gateway = None

    @property
    def gateway(self):
        if self._gateway is None:
            try:
                from sfc.ai.model_gateway import get_ai_gateway
                self._gateway = get_ai_gateway()
            except Exception:
                self._gateway = None
        return self._gateway

    async def analyze(
        self,
        ingestion_result: VideoIngestionResult,
    ) -> VideoUnderstandingResult:
        video_id = (
            ingestion_result.video_metadata.video_id
            if ingestion_result.video_metadata
            else ingestion_result.ingestion_id
        )
        source_path = ingestion_result.source.path

        if not is_video_processing_enabled():
            return self._dry_run_result(video_id, ingestion_result)

        transcript = await self._transcribe(video_id, source_path)
        scenes = await self._detect_scenes(video_id, source_path)
        frame_index = self._build_frame_index(video_id, source_path)
        summary = await self._summarize(transcript, scenes, ingestion_result)

        result = VideoUnderstandingResult(
            video_id=video_id,
            transcript=transcript,
            scenes=scenes,
            frame_index=frame_index,
            summary=summary,
            language_detected=transcript.language if transcript else "arabic",
        )
        logger.info(
            "[Understanding] video_id=%s scenes=%d has_transcript=%s",
            video_id,
            len(scenes),
            result.has_transcript,
        )
        return result

    async def _transcribe(
        self, video_id: str, path: str
    ) -> VideoTranscript:
        if WHISPER_API_KEY and path:
            real = await self._whisper_transcribe(video_id, path)
            if real:
                return real

        return VideoTranscript(
            video_id=video_id,
            segments=[],
            full_text="",
            provider="unavailable",
        )

    async def _whisper_transcribe(
        self, video_id: str, path: str
    ) -> VideoTranscript | None:
        from pathlib import Path
        if not Path(path).exists():
            return None
        try:
            import httpx
            async with httpx.AsyncClient(timeout=120) as client:
                with open(path, "rb") as f:
                    response = await client.post(
                        "https://api.openai.com/v1/audio/transcriptions",
                        headers={"Authorization": f"Bearer {WHISPER_API_KEY}"},
                        data={"model": "whisper-1", "response_format": "verbose_json"},
                        files={"file": (Path(path).name, f, "video/mp4")},
                    )
                response.raise_for_status()
                data = response.json()
            segments = [
                TranscriptSegment(
                    start_seconds=seg["start"],
                    end_seconds=seg["end"],
                    text=seg["text"].strip(),
                    language=data.get("language", "arabic"),
                )
                for seg in data.get("segments", [])
            ]
            return VideoTranscript(
                video_id=video_id,
                segments=segments,
                full_text=data.get("text", ""),
                language=data.get("language", "arabic"),
                provider="openai_whisper",
            )
        except Exception as exc:
            logger.warning("[Understanding] Whisper failed: %s", exc)
            return None

    async def _detect_scenes(
        self, video_id: str, path: str
    ) -> list[SceneSegment]:
        import shutil
        if not path or not shutil.which("ffprobe"):
            return []
        from pathlib import Path as P
        if not P(path).exists():
            return []
        try:
            import subprocess, json as j
            result = subprocess.run(
                [
                    "ffprobe", "-v", "quiet", "-print_format", "json",
                    "-show_frames", "-select_streams", "v",
                    "-skip_frame", "noref", path,
                ],
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode != 0:
                return []
            frames = j.loads(result.stdout).get("frames", [])
            scenes: list[SceneSegment] = []
            prev_ts = 0.0
            for frame in frames:
                tags = frame.get("tags", {})
                if "lavfi.scene_score" in tags and float(tags["lavfi.scene_score"]) > 0.3:
                    ts = float(frame.get("best_effort_timestamp_time", 0))
                    scenes.append(
                        SceneSegment(
                            start_seconds=prev_ts,
                            end_seconds=ts,
                            scene_type="scene_change",
                            confidence=float(tags["lavfi.scene_score"]),
                        )
                    )
                    prev_ts = ts
            return scenes
        except Exception as exc:
            logger.debug("[Understanding] Scene detection failed: %s", exc)
            return []

    def _build_frame_index(
        self, video_id: str, path: str
    ) -> VideoFrameIndex:
        return VideoFrameIndex(
            video_id=video_id,
            frame_count=0,
            sampled_frames=[],
            key_frame_timestamps=[],
        )

    async def _summarize(
        self,
        transcript: VideoTranscript,
        scenes: list[SceneSegment],
        ingestion: VideoIngestionResult,
    ) -> str:
        title = ingestion.source.title or "Untitled"
        n_scenes = len(scenes)
        has_speech = bool(transcript.segments)
        if self.gateway:
            try:
                from sfc.ai.model_gateway import ModelRequest
                snippet = transcript.full_text[:500] if transcript.full_text else ""
                result = await self.gateway.complete(
                    ModelRequest(
                        prompt=(
                            f"Summarize this Saudi football video in 2 sentences. "
                            f"Title: '{title}'. Scenes: {n_scenes}. "
                            f"Transcript excerpt: {snippet}"
                        ),
                        max_tokens=100,
                    )
                )
                return result.content.strip()
            except Exception:
                pass
        return (
            f"Video: {title}. "
            f"{n_scenes} scene segments detected. "
            f"{'Transcript available.' if has_speech else 'No transcript.'}"
        )

    def _dry_run_result(
        self,
        video_id: str,
        ingestion: VideoIngestionResult,
    ) -> VideoUnderstandingResult:
        title = ingestion.source.title or "Untitled"
        dummy_transcript = VideoTranscript(
            video_id=video_id,
            segments=[
                TranscriptSegment(
                    start_seconds=0.0,
                    end_seconds=30.0,
                    text=f"[DRY RUN] Transcript for: {title}",
                    language="arabic",
                    confidence=1.0,
                )
            ],
            full_text=f"[DRY RUN] Transcript for: {title}",
            language="arabic",
            provider="dry_run",
        )
        return VideoUnderstandingResult(
            video_id=video_id,
            transcript=dummy_transcript,
            scenes=[
                SceneSegment(
                    start_seconds=0.0,
                    end_seconds=60.0,
                    scene_type="dry_run",
                    confidence=1.0,
                    description=f"[DRY RUN] scene for {title}",
                )
            ],
            summary=f"[DRY RUN] {title}",
            dry_run=True,
        )
