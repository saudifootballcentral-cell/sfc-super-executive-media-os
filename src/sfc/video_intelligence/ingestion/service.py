"""Video Ingestion Service — validates, hashes, and stores video source metadata."""

from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path
from typing import Any

from sfc.video_intelligence.ingestion.models import (
    RightsStatus,
    VideoFrameIndex,
    VideoIngestionResult,
    VideoMetadata,
    VideoProcessingStatus,
    VideoResolution,
    VideoSource,
    VideoSourceType,
)
from sfc.video_intelligence.shared.constants import (
    VIDEO_STORAGE_ROOT,
    is_video_processing_enabled,
)

logger = logging.getLogger("sfc.video_intelligence.ingestion")

_singleton: "VideoIngestionService | None" = None


def get_video_ingestion_service() -> "VideoIngestionService":
    global _singleton
    if _singleton is None:
        _singleton = VideoIngestionService()
    return _singleton


class VideoIngestionService:
    """Ingests video sources, extracts metadata, deduplicates, and enforces rights."""

    def __init__(self) -> None:
        self._ingested: dict[str, VideoIngestionResult] = {}
        self._hash_index: dict[str, str] = {}  # hash → video_id

    async def ingest(
        self,
        source: VideoSource,
        run_id: str | None = None,
    ) -> VideoIngestionResult:
        result = VideoIngestionResult(source=source)
        result.log(f"Ingestion started: source_type={source.source_type.value}")

        # Rights gate — restricted sources are blocked immediately
        if source.rights_status == RightsStatus.RESTRICTED:
            result.status = VideoProcessingStatus.RIGHTS_BLOCKED
            result.error_message = "Source is marked RESTRICTED — processing blocked"
            result.log("BLOCKED: rights_status=restricted")
            logger.warning("[Ingestion] Rights blocked: %s", source.source_id)
            self._ingested[result.ingestion_id] = result
            return result

        if not is_video_processing_enabled():
            result.status = VideoProcessingStatus.DRY_RUN
            result.video_metadata = self._mock_metadata(source)
            result.log("DRY_RUN: VIDEO_PROCESSING_ENABLED=false, returning planning metadata")
            self._ingested[result.ingestion_id] = result
            return result

        result.status = VideoProcessingStatus.INGESTING

        # Compute source hash for deduplication
        source_hash = self._compute_source_hash(source)

        # Duplicate detection
        if source_hash in self._hash_index:
            existing_id = self._hash_index[source_hash]
            result.status = VideoProcessingStatus.DUPLICATE
            result.is_duplicate = True
            result.duplicate_of = existing_id
            result.error_message = f"Duplicate of video_id={existing_id}"
            result.log(f"DUPLICATE: matches {existing_id}")
            self._ingested[result.ingestion_id] = result
            return result

        # Extract metadata
        metadata = await self._extract_metadata(source, source_hash)
        result.video_metadata = metadata
        result.status = VideoProcessingStatus.ANALYZING

        # Register hash
        self._hash_index[source_hash] = metadata.video_id
        result.log(f"Ingestion complete: video_id={metadata.video_id} duration={metadata.duration_label}")
        logger.info(
            "[Ingestion] Ingested: %s | %s | %.0fs",
            metadata.video_id,
            metadata.resolution.label,
            metadata.duration_seconds,
        )

        self._ingested[result.ingestion_id] = result
        return result

    async def _extract_metadata(
        self, source: VideoSource, source_hash: str
    ) -> VideoMetadata:
        metadata = VideoMetadata(
            title=source.title or Path(source.path).stem if source.path else source.url,
            source_type=source.source_type,
            rights_status=source.rights_status,
            source_hash=source_hash,
        )

        # Try to use ffprobe for real metadata extraction
        if source.path and Path(source.path).exists():
            real = self._probe_file(source.path)
            if real:
                metadata.duration_seconds = real.get("duration", 0.0)
                metadata.fps = real.get("fps", 30.0)
                metadata.file_size_bytes = real.get("file_size", 0)
                metadata.codec = real.get("codec", "")
                metadata.bitrate_kbps = real.get("bitrate_kbps", 0)
                w = real.get("width", 1920)
                h = real.get("height", 1080)
                metadata.resolution = VideoResolution(width=w, height=h)
                return metadata

        # Fallback for URL sources or inaccessible files
        return metadata

    def _probe_file(self, path: str) -> dict[str, Any] | None:
        import shutil
        if not shutil.which("ffprobe"):
            return None
        import subprocess, json
        try:
            result = subprocess.run(
                [
                    "ffprobe", "-v", "quiet", "-print_format", "json",
                    "-show_streams", "-show_format", path,
                ],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                return None
            data = json.loads(result.stdout)
            fmt = data.get("format", {})
            video_stream = next(
                (s for s in data.get("streams", []) if s.get("codec_type") == "video"),
                {},
            )
            r_frame_rate = video_stream.get("r_frame_rate", "30/1")
            num, den = (int(x) for x in r_frame_rate.split("/"))
            fps = num / max(den, 1)
            return {
                "duration": float(fmt.get("duration", 0)),
                "fps": fps,
                "file_size": int(fmt.get("size", 0)),
                "codec": video_stream.get("codec_name", ""),
                "bitrate_kbps": int(int(fmt.get("bit_rate", 0)) / 1000),
                "width": video_stream.get("width", 1920),
                "height": video_stream.get("height", 1080),
            }
        except Exception:
            return None

    def _compute_source_hash(self, source: VideoSource) -> str:
        key = source.path or source.url or source.source_id
        if source.path and Path(source.path).exists():
            h = hashlib.sha256()
            with open(source.path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    h.update(chunk)
            return h.hexdigest()
        return hashlib.sha256(key.encode()).hexdigest()

    def _mock_metadata(self, source: VideoSource) -> VideoMetadata:
        return VideoMetadata(
            title=source.title or "Untitled Video",
            source_type=source.source_type,
            rights_status=source.rights_status,
            duration_seconds=120.0,
            fps=30.0,
            file_size_bytes=0,
            source_hash=hashlib.sha256(
                (source.path or source.url or source.source_id).encode()
            ).hexdigest(),
            metadata={"dry_run": True},
        )

    def get_ingestion(self, ingestion_id: str) -> VideoIngestionResult | None:
        return self._ingested.get(ingestion_id)

    def get_all_ingestions(self) -> list[VideoIngestionResult]:
        return list(self._ingested.values())

    def reset_for_test(self) -> None:
        self._ingested.clear()
        self._hash_index.clear()
