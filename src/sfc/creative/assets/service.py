"""Creative Asset Management Service — registry and lifecycle for all creative assets."""

from __future__ import annotations

import logging
from typing import Any

from sfc.creative.assets.models import (
    AssetRegistryReport,
    AssetStatus,
    AssetType,
    CreativeAsset,
)

logger = logging.getLogger("sfc.creative.assets")

_singleton: "AssetManagementService | None" = None


def get_asset_management_service() -> "AssetManagementService":
    global _singleton
    if _singleton is None:
        _singleton = AssetManagementService()
    return _singleton


class AssetManagementService:
    """Registry and lifecycle manager for all creative assets."""

    def __init__(self) -> None:
        self._registry: dict[str, CreativeAsset] = {}

    def register_asset(
        self,
        asset_type: AssetType,
        title: str,
        description: str = "",
        platform: str = "",
        file_url: str = "",
        metadata: dict[str, Any] | None = None,
        quality_score: float = 0.0,
        brand_alignment_score: float = 0.0,
        tags: list[str] | None = None,
        source_asset_id: str = "",
    ) -> CreativeAsset:
        """Register a new creative asset in the registry."""
        asset = CreativeAsset(
            asset_type=asset_type,
            status=AssetStatus.GENERATED,
            title=title,
            description=description,
            platform=platform,
            file_url=file_url,
            metadata=metadata or {},
            quality_score=quality_score,
            brand_alignment_score=brand_alignment_score,
            tags=tags or [],
            source_asset_id=source_asset_id,
        )
        self._registry[asset.asset_id] = asset
        logger.info(
            "[AssetManagement] Registered | type=%s title=%s id=%s",
            asset_type.value,
            title[:40],
            asset.asset_id[:8],
        )
        return asset

    def get_asset(self, asset_id: str) -> CreativeAsset | None:
        return self._registry.get(asset_id)

    def update_status(self, asset_id: str, status: AssetStatus) -> bool:
        asset = self._registry.get(asset_id)
        if not asset:
            return False
        asset.status = status
        logger.info("[AssetManagement] Status update | id=%s status=%s", asset_id[:8], status.value)
        return True

    def update_quality_scores(
        self,
        asset_id: str,
        quality_score: float,
        brand_alignment_score: float,
    ) -> bool:
        asset = self._registry.get(asset_id)
        if not asset:
            return False
        asset.quality_score = quality_score
        asset.brand_alignment_score = brand_alignment_score
        return True

    def get_by_type(self, asset_type: AssetType) -> list[CreativeAsset]:
        return [a for a in self._registry.values() if a.asset_type == asset_type]

    def get_by_status(self, status: AssetStatus) -> list[CreativeAsset]:
        return [a for a in self._registry.values() if a.status == status]

    def get_approved(self) -> list[CreativeAsset]:
        return self.get_by_status(AssetStatus.APPROVED)

    def get_pending_qc(self) -> list[CreativeAsset]:
        return self.get_by_status(AssetStatus.QC_PENDING)

    def register_image_asset(self, image_asset: Any) -> CreativeAsset:
        """Register an ImageAsset from the image factory."""
        primary_variant = next(
            (v for v in image_asset.variants if v.variant_id == image_asset.primary_variant_id),
            image_asset.variants[0] if image_asset.variants else None,
        )
        return self.register_asset(
            asset_type=AssetType.IMAGE,
            title=image_asset.title,
            description=f"Image: {image_asset.image_format.value}",
            platform=image_asset.platform,
            file_url=primary_variant.file_url if primary_variant else "",
            quality_score=primary_variant.quality_score if primary_variant else 0.0,
            brand_alignment_score=image_asset.brand_alignment_score,
            metadata={"image_format": image_asset.image_format.value, "variants": len(image_asset.variants)},
        )

    def register_video_asset(self, video_asset: Any) -> CreativeAsset:
        """Register a VideoAsset from the video factory."""
        return self.register_asset(
            asset_type=AssetType.VIDEO,
            title=video_asset.title,
            description=f"Video: {video_asset.video_format.value}",
            platform=video_asset.platform,
            file_url=video_asset.file_url,
            quality_score=video_asset.estimated_completion_rate,
            brand_alignment_score=video_asset.brand_alignment_score,
            metadata={
                "video_format": video_asset.video_format.value,
                "duration_seconds": video_asset.duration_seconds,
                "provider": video_asset.provider.value,
            },
        )

    def register_shorts_package(self, shorts_package: Any) -> CreativeAsset:
        """Register a ShortsPackage from the shorts factory."""
        return self.register_asset(
            asset_type=AssetType.SHORTS_PACKAGE,
            title=shorts_package.title,
            description=f"Shorts: {shorts_package.platform.value}",
            platform=shorts_package.platform.value,
            metadata={
                "duration_seconds": shorts_package.duration_seconds,
                "hashtag_count": len(shorts_package.hashtags),
            },
        )

    def register_podcast_episode(self, episode: Any) -> CreativeAsset:
        """Register a PodcastEpisode from the podcast factory."""
        return self.register_asset(
            asset_type=AssetType.PODCAST_EPISODE,
            title=episode.episode_title,
            description=f"Podcast: {episode.podcast_type.value} EP{episode.episode_number}",
            platform="spotify",
            metadata={
                "podcast_type": episode.podcast_type.value,
                "episode_number": episode.episode_number,
                "duration_minutes": episode.total_duration_minutes,
                "segment_count": len(episode.segments),
            },
        )

    def generate_registry_report(self) -> AssetRegistryReport:
        """Generate a summary report of all registered assets."""
        assets = list(self._registry.values())
        by_type: dict[str, int] = {}
        by_status: dict[str, int] = {}
        for asset in assets:
            by_type[asset.asset_type.value] = by_type.get(asset.asset_type.value, 0) + 1
            by_status[asset.status.value] = by_status.get(asset.status.value, 0) + 1

        quality_scores = [a.quality_score for a in assets if a.quality_score > 0]
        avg_quality = sum(quality_scores) / max(len(quality_scores), 1)
        approved = sum(1 for a in assets if a.status == AssetStatus.APPROVED)
        rejected = sum(1 for a in assets if a.status == AssetStatus.REJECTED)

        return AssetRegistryReport(
            assets=assets,
            total_assets=len(assets),
            assets_by_type=by_type,
            assets_by_status=by_status,
            avg_quality_score=round(avg_quality, 1),
            approved_count=approved,
            rejected_count=rejected,
        )

    @property
    def total_assets(self) -> int:
        return len(self._registry)
