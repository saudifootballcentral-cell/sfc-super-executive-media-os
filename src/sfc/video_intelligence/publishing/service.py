"""Clip Publishing Integration — routes approved clip packages to publishers."""

from __future__ import annotations

import logging

from sfc.video_intelligence.governance.models import ClipGovernanceResult, ClipGovernanceStatus
from sfc.video_intelligence.packaging.models import ClipPackage

logger = logging.getLogger("sfc.video_intelligence.publishing")

_singleton: "ClipPublishingIntegration | None" = None


def get_clip_publishing_integration() -> "ClipPublishingIntegration":
    global _singleton
    if _singleton is None:
        _singleton = ClipPublishingIntegration()
    return _singleton


class ClipPublishingIntegration:
    """Bridges clip packages into the existing ContentPackagingService pipeline."""

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

        try:
            from sfc.creative.packaging.service import get_content_packaging_service
            from sfc.creative.packaging.models import PackageType
        except ImportError:
            return {
                "status": "error",
                "reason": "ContentPackagingService unavailable",
                "clip_id": package.clip_id,
            }

        packaging_svc = get_content_packaging_service()
        best_platform = (
            package.variants[0].platform if package.variants else "multi"
        )
        pkg_type = self._platform_to_package_type(best_platform)

        content_package = await packaging_svc.create_package(
            package_type=pkg_type,
            title=package.title,
            description=package.description,
            hashtags=package.hashtags,
            quality_score=package.quality_score,
            governance_cleared=governance.status == ClipGovernanceStatus.APPROVED,
            media_assets=[
                {
                    "clip_id": package.clip_id,
                    "platform": v.platform,
                    "local_path": v.local_path,
                    "duration_seconds": v.duration_seconds,
                }
                for v in package.variants
            ],
            publishing_metadata={"source": "video_intelligence"},
        )

        record = {
            "status": "submitted",
            "clip_id": package.clip_id,
            "package_id": package.package_id,
            "content_package_id": content_package.package_id,
            "platform": best_platform,
            "ready_to_publish": content_package.ready_to_publish,
        }
        package.published = content_package.ready_to_publish
        self._published.append(record)

        logger.info(
            "[Publishing] clip_id=%s → content_package=%s ready=%s",
            package.clip_id,
            content_package.package_id,
            content_package.ready_to_publish,
        )
        return record

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
