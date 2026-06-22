"""Clip Enhancement Engine — platform-specific variants and aspect ratio cropping."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from sfc.video_intelligence.clipping.models import VideoClip
from sfc.video_intelligence.enhancement.models import (
    AspectRatio,
    EnhancedClipVariant,
    EnhancementResult,
)
from sfc.video_intelligence.scoring.models import ClipScore
from sfc.video_intelligence.shared.constants import (
    CLIP_STORAGE_ROOT,
    is_video_processing_enabled,
)

logger = logging.getLogger("sfc.video_intelligence.enhancement")

_singleton: "ClipEnhancementEngine | None" = None

FFMPEG_AVAILABLE = bool(shutil.which("ffmpeg"))

_PLATFORM_ASPECT: dict[str, AspectRatio] = {
    "youtube_short": AspectRatio.PORTRAIT_9_16,
    "instagram_reel": AspectRatio.PORTRAIT_9_16,
    "tiktok": AspectRatio.PORTRAIT_9_16,
    "x_video": AspectRatio.LANDSCAPE_16_9,
    "youtube_video": AspectRatio.LANDSCAPE_16_9,
}


def get_clip_enhancement_engine() -> "ClipEnhancementEngine":
    global _singleton
    if _singleton is None:
        _singleton = ClipEnhancementEngine()
    return _singleton


class ClipEnhancementEngine:
    """Creates platform-specific clip variants with correct aspect ratios."""

    def __init__(self, storage_root: str | None = None) -> None:
        self._storage_root = Path(storage_root or CLIP_STORAGE_ROOT)

    async def enhance(
        self, clip: VideoClip, score: ClipScore
    ) -> EnhancementResult:
        result = EnhancementResult(clip_id=clip.clip_id)

        # Determine target platforms from score
        target_platforms = [
            ps.platform
            for ps in score.platform_scores
            if ps.suitability_score >= 60 and ps.within_duration_limit
        ][:3]  # max 3 platforms per clip

        if not is_video_processing_enabled():
            result.dry_run = True
            for platform in target_platforms:
                aspect = _PLATFORM_ASPECT.get(platform, AspectRatio.LANDSCAPE_16_9)
                result.variants.append(
                    EnhancedClipVariant(
                        clip_id=clip.clip_id,
                        platform=platform,
                        aspect_ratio=aspect,
                        duration_seconds=clip.duration_seconds,
                        ready=True,
                        metadata={"dry_run": True},
                    )
                )
            return result

        enhanced_dir = self._storage_root / "enhanced"
        enhanced_dir.mkdir(parents=True, exist_ok=True)

        for platform in target_platforms:
            aspect = _PLATFORM_ASPECT.get(platform, AspectRatio.LANDSCAPE_16_9)
            variant = await self._create_variant(clip, platform, aspect, enhanced_dir)
            result.variants.append(variant)

        logger.info(
            "[Enhancement] clip_id=%s variants=%d",
            clip.clip_id,
            len(result.variants),
        )
        return result

    async def _create_variant(
        self,
        clip: VideoClip,
        platform: str,
        aspect: AspectRatio,
        out_dir: Path,
    ) -> EnhancedClipVariant:
        variant = EnhancedClipVariant(
            clip_id=clip.clip_id,
            platform=platform,
            aspect_ratio=aspect,
            duration_seconds=clip.duration_seconds,
        )

        if not clip.local_path or not Path(clip.local_path).exists():
            variant.metadata["error"] = "source clip not available"
            return variant

        out_path = out_dir / f"{clip.clip_id}_{platform}.mp4"

        if FFMPEG_AVAILABLE:
            vf = self._vf_filter(aspect)
            success = await self._ffmpeg_convert(
                clip.local_path, str(out_path), vf
            )
            if success and out_path.exists():
                variant.local_path = str(out_path)
                variant.file_size_bytes = out_path.stat().st_size
                variant.ready = True
                return variant

        variant.metadata["error"] = "ffmpeg unavailable"
        return variant

    def _vf_filter(self, aspect: AspectRatio) -> str:
        if aspect == AspectRatio.PORTRAIT_9_16:
            return "crop=ih*9/16:ih,scale=1080:1920"
        if aspect == AspectRatio.SQUARE_1_1:
            return "crop=ih:ih,scale=1080:1080"
        return "scale=1920:1080"  # 16:9 default

    async def _ffmpeg_convert(
        self, src: str, dst: str, vf: str
    ) -> bool:
        import asyncio
        cmd = [
            "ffmpeg", "-y", "-i", src,
            "-vf", vf,
            "-c:v", "libx264", "-c:a", "aac",
            "-movflags", "+faststart", dst,
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
