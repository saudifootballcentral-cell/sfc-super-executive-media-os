"""Clip Publishing Integration — routes approved clip packages to platform publishers.

Dispatch order per variant platform:
  youtube_short / youtube_video → connectors.youtube.publisher.YouTubeVideoPublisher
  instagram_reel                → connectors.instagram.publisher.InstagramReelPublisher
  x_video / tiktok / others    → ContentPackagingService (Buffer / existing pipeline)

All dispatches are best-effort: a single platform failure does not abort
publishing to other platforms.
"""

from __future__ import annotations

import logging

from sfc.video_intelligence.governance.models import ClipGovernanceResult, ClipGovernanceStatus
from sfc.video_intelligence.packaging.models import ClipPackage, PlatformClipVariant

logger = logging.getLogger("sfc.video_intelligence.publishing")

_singleton: "ClipPublishingIntegration | None" = None

_YOUTUBE_PLATFORMS = {"youtube_short", "youtube_video"}
_INSTAGRAM_PLATFORMS = {"instagram_reel"}


def get_clip_publishing_integration() -> "ClipPublishingIntegration":
    global _singleton
    if _singleton is None:
        _singleton = ClipPublishingIntegration()
    return _singleton


class ClipPublishingIntegration:
    """Bridges clip packages into platform-specific publishers."""

    def __init__(self) -> None:
        self._published: list[dict] = []

    async def publish(
        self,
        package: ClipPackage,
        governance: ClipGovernanceResult,
    ) -> dict:
        if not governance.cleared_for_publishing:
            return {
                "status": "blocked",
                "reason": f"Governance: {governance.status.value}",
                "clip_id": package.clip_id,
                "issues": governance.issues,
            }

        publishable = package.publishable_variants or package.variants
        if not publishable:
            return {
                "status": "error",
                "reason": "No variants to publish",
                "clip_id": package.clip_id,
            }

        platform_results: list[dict] = []
        any_published = False

        for variant in publishable:
            result = await self._dispatch(package, variant)
            platform_results.append(result)
            if result.get("status") in ("published", "submitted"):
                any_published = True

        package.published = any_published

        record = {
            "status": "submitted" if any_published else "failed",
            "clip_id": package.clip_id,
            "package_id": package.package_id,
            "platform_results": platform_results,
        }
        self._published.append(record)

        logger.info(
            "[Publishing] clip_id=%s platforms=%s published=%s",
            package.clip_id,
            [r.get("platform", r.get("status")) for r in platform_results],
            any_published,
        )
        return record

    async def _dispatch(self, package: ClipPackage, variant: PlatformClipVariant) -> dict:
        """Route a single variant to the correct platform publisher."""
        platform = variant.platform

        if platform in _YOUTUBE_PLATFORMS:
            return await self._publish_youtube(package, variant)

        if platform in _INSTAGRAM_PLATFORMS:
            return await self._publish_instagram(package, variant)

        # All other platforms: Buffer / ContentPackagingService
        return await self._publish_via_content_pipeline(package, variant)

    async def _publish_youtube(
        self, package: ClipPackage, variant: PlatformClipVariant
    ) -> dict:
        try:
            from sfc.connectors.youtube.publisher import YouTubeVideoPublisher
            publisher = YouTubeVideoPublisher()
            return await publisher.publish(package, variant, attribution=package.attribution)
        except Exception as exc:
            logger.error("[Publishing] YouTube dispatch failed clip_id=%s: %s", package.clip_id, exc)
            return {"status": "failed", "platform": variant.platform, "error": str(exc)}

    async def _publish_instagram(
        self, package: ClipPackage, variant: PlatformClipVariant
    ) -> dict:
        try:
            from sfc.connectors.instagram.publisher import InstagramReelPublisher
            publisher = InstagramReelPublisher()
            # Instagram needs a public URL; pass public_url from rendering metadata if available
            public_url = variant.metadata.get("public_url", "")
            return await publisher.publish(
                package, variant,
                public_video_url=public_url,
                attribution=package.attribution,
            )
        except Exception as exc:
            logger.error("[Publishing] Instagram dispatch failed clip_id=%s: %s", package.clip_id, exc)
            return {"status": "failed", "platform": variant.platform, "error": str(exc)}

    async def _publish_via_content_pipeline(
        self, package: ClipPackage, variant: PlatformClipVariant
    ) -> dict:
        """Fallback: route through ContentPackagingService (Buffer / X)."""
        try:
            from sfc.creative.packaging.service import get_content_packaging_service
            from sfc.creative.packaging.models import PackageType
        except ImportError:
            return {
                "status": "error",
                "reason": "ContentPackagingService unavailable",
                "platform": variant.platform,
                "clip_id": package.clip_id,
            }

        packaging_svc = get_content_packaging_service()
        pkg_type = self._platform_to_package_type(variant.platform)

        try:
            content_package = await packaging_svc.create_package(
                package_type=pkg_type,
                title=package.title,
                description=package.description,
                hashtags=package.hashtags,
                quality_score=package.quality_score,
                governance_cleared=True,
                media_assets=[{
                    "clip_id": package.clip_id,
                    "platform": variant.platform,
                    "local_path": variant.local_path,
                    "duration_seconds": variant.duration_seconds,
                    "attribution": package.attribution,
                }],
                publishing_metadata={"source": "video_intelligence"},
            )
            return {
                "status": "submitted",
                "platform": variant.platform,
                "content_package_id": content_package.package_id,
                "ready_to_publish": content_package.ready_to_publish,
                "clip_id": package.clip_id,
            }
        except Exception as exc:
            logger.error(
                "[Publishing] ContentPipeline dispatch failed clip_id=%s platform=%s: %s",
                package.clip_id, variant.platform, exc,
            )
            return {"status": "failed", "platform": variant.platform, "error": str(exc)}

    def _platform_to_package_type(self, platform: str):
        from sfc.creative.packaging.models import PackageType
        mapping = {
            "youtube_short": PackageType.YOUTUBE_SHORT,
            "youtube_video": PackageType.YOUTUBE_VIDEO,
            "instagram_reel": PackageType.INSTAGRAM,
            "tiktok": PackageType.TIKTOK,
            "x_video": PackageType.X_THREAD,
            "podcast": PackageType.PODCAST,
        }
        return mapping.get(platform, PackageType.YOUTUBE_SHORT)

    def get_published(self) -> list[dict]:
        return list(self._published)

    def reset_for_test(self) -> None:
        self._published.clear()
