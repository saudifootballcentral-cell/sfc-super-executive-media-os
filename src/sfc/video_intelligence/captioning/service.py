"""Auto Captioning & Subtitle Engine."""

from __future__ import annotations

import logging
from pathlib import Path

from sfc.video_intelligence.captioning.models import (
    CaptionEntry,
    CaptioningResult,
    SubtitleTrack,
)
from sfc.video_intelligence.clipping.models import VideoClip
from sfc.video_intelligence.shared.constants import (
    CLIP_STORAGE_ROOT,
    is_video_processing_enabled,
)
from sfc.video_intelligence.understanding.models import VideoTranscript

logger = logging.getLogger("sfc.video_intelligence.captioning")

_singleton: "AutoCaptioningEngine | None" = None


def get_auto_captioning_engine() -> "AutoCaptioningEngine":
    global _singleton
    if _singleton is None:
        _singleton = AutoCaptioningEngine()
    return _singleton


def _seconds_to_srt_time(seconds: float) -> str:
    total_ms = int(seconds * 1000)
    ms = total_ms % 1000
    total_s = total_ms // 1000
    s = total_s % 60
    m = (total_s // 60) % 60
    h = total_s // 3600
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


class AutoCaptioningEngine:
    """Generates SRT subtitle tracks for clips from transcripts."""

    def __init__(self, storage_root: str | None = None) -> None:
        self._storage_root = Path(storage_root or CLIP_STORAGE_ROOT)
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

    async def caption(
        self,
        clip: VideoClip,
        transcript: VideoTranscript | None,
    ) -> CaptioningResult:
        result = CaptioningResult(clip_id=clip.clip_id)

        if not is_video_processing_enabled():
            result.dry_run = True
            result.tracks = self._dry_run_tracks(clip)
            return result

        if transcript and transcript.segments:
            # Extract segments that overlap with this clip
            clip_segs = transcript.segments_in_range(
                clip.start_seconds, clip.end_seconds
            )
            if clip_segs:
                for lang in ("arabic", "english"):
                    track = await self._build_track(clip, clip_segs, lang)
                    track = self._save_track(track)
                    result.tracks.append(track)

        logger.info(
            "[Captioning] clip_id=%s tracks=%d",
            clip.clip_id,
            len(result.tracks),
        )
        return result

    async def _build_track(
        self, clip: VideoClip, segments: list, language: str
    ) -> SubtitleTrack:
        track = SubtitleTrack(
            clip_id=clip.clip_id,
            language=language,
        )
        offset = clip.start_seconds
        for i, seg in enumerate(segments, start=1):
            text = seg.text
            if language == "english" and self.gateway:
                text = await self._translate_to_english(seg.text)
            start_rel = max(0.0, seg.start_seconds - offset)
            end_rel = seg.end_seconds - offset
            track.entries.append(
                CaptionEntry(
                    index=i,
                    start_time=_seconds_to_srt_time(start_rel),
                    end_time=_seconds_to_srt_time(end_rel),
                    text=text,
                    language=language,
                )
            )
        return track

    async def _translate_to_english(self, text: str) -> str:
        if not self.gateway:
            return text
        try:
            from sfc.ai.model_gateway import ModelRequest
            result = await self.gateway.complete(
                ModelRequest(
                    prompt=f"Translate to English (sports context): {text}",
                    max_tokens=80,
                )
            )
            return result.content.strip()
        except Exception:
            return text

    def _save_track(self, track: SubtitleTrack) -> SubtitleTrack:
        srt_dir = self._storage_root / "subtitles"
        srt_dir.mkdir(parents=True, exist_ok=True)
        path = srt_dir / f"{track.clip_id}_{track.language}.srt"
        try:
            path.write_text(track.to_srt(), encoding="utf-8")
            track.local_path = str(path)
        except Exception as exc:
            logger.debug("[Captioning] Could not save track: %s", exc)
        return track

    def _dry_run_tracks(self, clip: VideoClip) -> list[SubtitleTrack]:
        tracks = []
        for lang in ("arabic", "english"):
            track = SubtitleTrack(
                clip_id=clip.clip_id,
                language=lang,
                entries=[
                    CaptionEntry(
                        index=1,
                        start_time="00:00:00,000",
                        end_time=_seconds_to_srt_time(
                            min(clip.duration_seconds, 10.0)
                        ),
                        text=f"[DRY RUN] {clip.title}",
                        language=lang,
                    )
                ],
            )
            tracks.append(track)
        return tracks
