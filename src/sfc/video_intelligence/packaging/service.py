"""Clip Packaging Engine — assembles platform-ready clip packages."""

from __future__ import annotations

import logging

from sfc.video_intelligence.captioning.models import CaptioningResult
from sfc.video_intelligence.clipping.models import VideoClip
from sfc.video_intelligence.enhancement.models import EnhancementResult
from sfc.video_intelligence.packaging.models import ClipPackage, PlatformClipVariant
from sfc.video_intelligence.scoring.models import ClipScore

logger = logging.getLogger("sfc.video_intelligence.packaging")

_singleton: "ClipPackagingEngine | None" = None

_DEFAULT_HASHTAGS = ["#SFC", "#SaudiFootball", "#الدوري_السعودي", "#SPL"]

_PLATFORM_HASHTAGS: dict[str, list[str]] = {
    "youtube_short": ["#Shorts", "#Football"],
    "instagram_reel": ["#Reels", "#Football"],
    "tiktok": ["#TikTok", "#Football", "#viral"],
    "x_video": ["#SPL", "#Thread"],
    "youtube_video": ["#YouTube", "#SPL"],
}


def get_clip_packaging_engine() -> "ClipPackagingEngine":
    global _singleton
    if _singleton is None:
        _singleton = ClipPackagingEngine()
    return _singleton


class ClipPackagingEngine:
    """Assembles ClipPackage objects from clip, enhancement, captioning, and score."""

    def __init__(self) -> None:
        self._packages: list[ClipPackage] = []

    async def package(
        self,
        clip: VideoClip,
        score: ClipScore,
        enhancement: EnhancementResult,
        captioning: CaptioningResult,
    ) -> ClipPackage:
        hashtags = list(_DEFAULT_HASHTAGS)

        variants = self._build_variants(
            clip, score, enhancement, captioning
        )

        package = ClipPackage(
            clip_id=clip.clip_id,
            video_id=clip.video_id,
            title=clip.title,
            description=clip.description,
            clip_type=clip.clip_type,
            hashtags=hashtags,
            variants=variants,
            quality_score=score.overall_score,
            dry_run=enhancement.dry_run,
        )

        # Add platform-specific hashtags for each variant's platform
        for variant in variants:
            extra = _PLATFORM_HASHTAGS.get(variant.platform, [])
            for tag in extra:
                if tag not in package.hashtags:
                    package.hashtags.append(tag)

        self._packages.append(package)
        logger.info(
            "[Packaging] clip_id=%s variants=%d quality=%.1f",
            clip.clip_id,
            len(variants),
            score.overall_score,
        )
        return package

    def _build_variants(
        self,
        clip: VideoClip,
        score: ClipScore,
        enhancement: EnhancementResult,
        captioning: CaptioningResult,
    ) -> list[PlatformClipVariant]:
        variants: list[PlatformClipVariant] = []

        # Map enhancement variants → packaging variants
        for ev in enhancement.variants:
            caption_track = captioning.track_for("arabic")
            caption_path = caption_track.local_path if caption_track else ""

            ps = next(
                (p for p in score.platform_scores if p.platform == ev.platform),
                None,
            )
            ready = ev.ready and (ps is not None and ps.suitability_score >= 60)

            variants.append(
                PlatformClipVariant(
                    platform=ev.platform,
                    aspect_ratio=ev.aspect_ratio.value,
                    duration_seconds=ev.duration_seconds,
                    local_path=ev.local_path,
                    thumbnail_path=clip.thumbnail_path,
                    caption_path=caption_path,
                    file_size_bytes=ev.file_size_bytes,
                    ready_to_publish=ready,
                    metadata={"dry_run": enhancement.dry_run},
                )
            )

        # Fallback: if no enhancement variants, add a single reference variant
        if not variants and score.best_platform:
            ps = score.best_platform_score()
            variants.append(
                PlatformClipVariant(
                    platform=score.best_platform,
                    aspect_ratio=ps.recommended_format if ps else "16:9",
                    duration_seconds=clip.duration_seconds,
                    local_path=clip.local_path,
                    ready_to_publish=False,
                    metadata={"fallback": True, "dry_run": enhancement.dry_run},
                )
            )

        return variants

    def get_packages(self) -> list[ClipPackage]:
        return list(self._packages)

    def reset_for_test(self) -> None:
        self._packages.clear()
