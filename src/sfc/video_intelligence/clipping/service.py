"""Smart Clipping Engine — extracts video clips from detected events and quotes."""

from __future__ import annotations

import hashlib
import logging
import shutil
from pathlib import Path
from typing import Any

from sfc.video_intelligence.clipping.models import (
    ClipRequest,
    ClipSourceType,
    ClipStatus,
    VideoClip,
)
from sfc.video_intelligence.event_detection.models import EventDetectionResult
from sfc.video_intelligence.ingestion.models import VideoIngestionResult
from sfc.video_intelligence.interview_detection.models import InterviewDetectionResult
from sfc.video_intelligence.shared.constants import (
    CLIP_STORAGE_ROOT,
    MAX_CLIP_DURATION,
    MIN_CLIP_DURATION,
    is_video_processing_enabled,
)

logger = logging.getLogger("sfc.video_intelligence.clipping")

_singleton: "SmartClippingEngine | None" = None

FFMPEG_AVAILABLE = bool(shutil.which("ffmpeg"))


def get_smart_clipping_engine() -> "SmartClippingEngine":
    global _singleton
    if _singleton is None:
        _singleton = SmartClippingEngine()
    return _singleton


class SmartClippingEngine:
    """Extracts publishable clips from detected sport events and interview quotes."""

    def __init__(self, storage_root: str | None = None) -> None:
        self._storage_root = Path(storage_root or CLIP_STORAGE_ROOT)
        self._clips: list[VideoClip] = []

    def _ensure_dirs(self) -> None:
        for sub in ("clips", "thumbnails"):
            (self._storage_root / sub).mkdir(parents=True, exist_ok=True)

    async def extract_clips(
        self,
        ingestion: VideoIngestionResult,
        events: EventDetectionResult,
        interviews: InterviewDetectionResult,
    ) -> list[VideoClip]:
        video_path = ingestion.source.path
        video_id = events.video_id

        requests = self._build_requests(video_id, video_path, events, interviews)

        if not is_video_processing_enabled():
            clips = [self._dry_run_clip(req) for req in requests]
            self._clips.extend(clips)
            return clips

        self._ensure_dirs()
        clips: list[VideoClip] = []
        for req in requests:
            clip = await self._extract_one(req, video_path)
            clips.append(clip)

        self._clips.extend(clips)
        logger.info(
            "[Clipping] video_id=%s clips=%d ready=%d",
            video_id,
            len(clips),
            sum(1 for c in clips if c.status == ClipStatus.READY),
        )
        return clips

    def _build_requests(
        self,
        video_id: str,
        video_path: str,
        events: EventDetectionResult,
        interviews: InterviewDetectionResult,
    ) -> list[ClipRequest]:
        requests: list[ClipRequest] = []

        # Build from sport events
        for event in events.top_events(n=5):
            duration = event.clip_end - event.clip_start
            if not (MIN_CLIP_DURATION <= duration <= MAX_CLIP_DURATION):
                continue
            requests.append(
                ClipRequest(
                    video_id=video_id,
                    video_path=video_path,
                    title=f"{event.event_type.value.replace('_', ' ').title()} — SFC",
                    description=event.description,
                    start_seconds=event.clip_start,
                    end_seconds=min(event.clip_end, event.clip_start + MAX_CLIP_DURATION),
                    clip_type=event.event_type.value,
                    source_type=ClipSourceType.SPORT_EVENT,
                    source_event_id=event.event_id,
                    metadata={"highlight_score": event.highlight_score},
                )
            )

        # Build from key quotes
        for quote in interviews.top_quotes(n=3):
            duration = quote.clip_end - quote.clip_start
            if not (MIN_CLIP_DURATION <= duration <= MAX_CLIP_DURATION):
                continue
            requests.append(
                ClipRequest(
                    video_id=video_id,
                    video_path=video_path,
                    title=f"Quote: {quote.speaker_name or 'Speaker'} — SFC",
                    description=quote.text[:100],
                    start_seconds=quote.clip_start,
                    end_seconds=min(quote.clip_end, quote.clip_start + MAX_CLIP_DURATION),
                    clip_type="key_quote",
                    source_type=ClipSourceType.KEY_QUOTE,
                    source_quote_id=quote.quote_id,
                    metadata={"importance_score": quote.importance_score},
                )
            )

        return requests

    async def _extract_one(
        self, request: ClipRequest, video_path: str
    ) -> VideoClip:
        clip = VideoClip(
            video_id=request.video_id,
            title=request.title,
            description=request.description,
            start_seconds=request.start_seconds,
            end_seconds=request.end_seconds,
            clip_type=request.clip_type,
            source_type=request.source_type,
            source_event_id=request.source_event_id,
            source_quote_id=request.source_quote_id,
            language=request.language,
            status=ClipStatus.EXTRACTING,
            metadata=request.metadata,
        )

        out_path = self._storage_root / "clips" / f"{clip.clip_id}.mp4"

        if FFMPEG_AVAILABLE and video_path and Path(video_path).exists():
            success = await self._ffmpeg_extract(
                video_path,
                str(out_path),
                request.start_seconds,
                request.end_seconds,
            )
            if success and out_path.exists() and out_path.stat().st_size > 0:
                clip.local_path = str(out_path)
                clip.file_size_bytes = out_path.stat().st_size
                clip.checksum_sha256 = self._checksum(str(out_path))
                clip.status = ClipStatus.READY
                return clip

        # No real file available — reference clip (analysis only, no cut)
        clip.local_path = video_path or ""
        clip.status = ClipStatus.FAILED
        clip.metadata["error"] = "ffmpeg unavailable or source file missing"
        return clip

    async def _ffmpeg_extract(
        self, src: str, dst: str, start: float, end: float
    ) -> bool:
        import asyncio
        duration = end - start
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start),
            "-i", src,
            "-t", str(duration),
            "-c:v", "libx264", "-c:a", "aac",
            "-movflags", "+faststart",
            dst,
        ]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(proc.communicate(), timeout=120)
            return proc.returncode == 0
        except Exception:
            return False

    def _checksum(self, path: str) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    def _dry_run_clip(self, request: ClipRequest) -> VideoClip:
        return VideoClip(
            video_id=request.video_id,
            title=request.title,
            description=request.description,
            start_seconds=request.start_seconds,
            end_seconds=request.end_seconds,
            clip_type=request.clip_type,
            source_type=request.source_type,
            source_event_id=request.source_event_id,
            source_quote_id=request.source_quote_id,
            language=request.language,
            status=ClipStatus.DRY_RUN,
            metadata={**request.metadata, "dry_run": True},
        )

    def get_clips(self) -> list[VideoClip]:
        return list(self._clips)

    def reset_for_test(self) -> None:
        self._clips.clear()
