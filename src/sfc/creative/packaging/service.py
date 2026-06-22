"""Content Packaging Engine — assembles platform-ready content packages."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from sfc.creative.packaging.models import (
    ContentPackage,
    PackagingReport,
    PackageType,
    PublishingMetadata,
)

logger = logging.getLogger("sfc.creative.packaging")

_singleton: "ContentPackagingService | None" = None


def get_content_packaging_service() -> "ContentPackagingService":
    global _singleton
    if _singleton is None:
        _singleton = ContentPackagingService()
    return _singleton


class ContentPackagingService:
    """Assembles and validates platform-ready content packages."""

    _QUALITY_THRESHOLD = 70.0

    def __init__(self) -> None:
        self._gateway = None
        self._packages: list[ContentPackage] = []

    @property
    def gateway(self):
        if self._gateway is None:
            try:
                from sfc.ai.model_gateway import get_ai_gateway
                self._gateway = get_ai_gateway()
            except Exception:
                self._gateway = None
        return self._gateway

    async def create_package(
        self,
        package_type: PackageType,
        title: str,
        description: str = "",
        caption: str = "",
        hashtags: list[str] | None = None,
        thumbnail_url: str = "",
        media_asset_ids: list[str] | None = None,
        media_assets: list[dict[str, Any]] | None = None,
        quality_score: float = 0.0,
        governance_cleared: bool = False,
        publishing_metadata: dict[str, Any] | None = None,
    ) -> ContentPackage:
        """Create a content package and validate it for publishing readiness."""
        meta_dict = publishing_metadata or {}
        pub_meta = PublishingMetadata(
            platform=meta_dict.get("platform", self._platform_for(package_type)),
            target_audience=meta_dict.get("target_audience", "Saudi football fans"),
            language=meta_dict.get("language", "arabic"),
            requires_approval=meta_dict.get("requires_approval", True),
            category=meta_dict.get("category", "sports"),
            boost_budget_usd=meta_dict.get("boost_budget_usd", 0.0),
            geo_targeting=meta_dict.get("geo_targeting", ["SA", "AE", "QA", "KW"]),
        )

        if not caption:
            caption = await self._generate_caption(title, package_type)

        package = ContentPackage(
            package_type=package_type,
            title=title,
            description=description or f"SFC {package_type.value.replace('_', ' ')} content",
            caption=caption,
            hashtags=hashtags or self._default_hashtags(package_type),
            thumbnail_url=thumbnail_url,
            media_asset_ids=media_asset_ids or [],
            media_assets=media_assets or [],
            publishing_metadata=pub_meta,
            quality_score=quality_score,
            governance_cleared=governance_cleared,
            ready_to_publish=self._is_ready(quality_score, governance_cleared),
        )
        self._packages.append(package)
        logger.info(
            "[ContentPackaging] Package created | type=%s title=%s ready=%s quality=%.0f",
            package_type.value,
            title[:40],
            package.ready_to_publish,
            quality_score,
        )
        return package

    async def package_from_assets(
        self,
        package_type: PackageType,
        title: str,
        assets: list[Any],
        quality_score: float = 0.0,
        governance_cleared: bool = False,
    ) -> ContentPackage:
        """Build a package directly from creative asset objects."""
        media_assets = []
        thumbnail_url = ""
        for asset in assets:
            asset_dict = asset.to_dict() if hasattr(asset, "to_dict") else {}
            media_assets.append(asset_dict)
            if not thumbnail_url and hasattr(asset, "thumbnail_url"):
                thumbnail_url = asset.thumbnail_url

        return await self.create_package(
            package_type=package_type,
            title=title,
            media_assets=media_assets,
            thumbnail_url=thumbnail_url,
            quality_score=quality_score,
            governance_cleared=governance_cleared,
        )

    async def generate_packaging_report(
        self, packages: list[ContentPackage] | None = None
    ) -> PackagingReport:
        """Generate a summary report for a set of packages."""
        packages = packages or self._packages
        total = len(packages)
        ready = sum(1 for p in packages if p.ready_to_publish)
        by_type: dict[str, int] = {}
        for p in packages:
            by_type[p.package_type.value] = by_type.get(p.package_type.value, 0) + 1
        avg_quality = (
            sum(p.quality_score for p in packages) / max(total, 1)
        )
        return PackagingReport(
            packages=packages,
            total_packages=total,
            ready_to_publish=ready,
            packages_by_type=by_type,
            avg_quality_score=round(avg_quality, 1),
        )

    def mark_governance_cleared(self, package_id: str) -> bool:
        for pkg in self._packages:
            if pkg.package_id == package_id:
                pkg.governance_cleared = True
                pkg.ready_to_publish = self._is_ready(pkg.quality_score, True)
                return True
        return False

    def _is_ready(self, quality_score: float, governance_cleared: bool) -> bool:
        return quality_score >= self._QUALITY_THRESHOLD and governance_cleared

    def _platform_for(self, package_type: PackageType) -> str:
        mapping = {
            PackageType.X_THREAD: "x",
            PackageType.YOUTUBE_SHORT: "youtube",
            PackageType.YOUTUBE_VIDEO: "youtube",
            PackageType.INSTAGRAM: "instagram",
            PackageType.TIKTOK: "tiktok",
            PackageType.PODCAST: "spotify",
        }
        return mapping.get(package_type, "multi")

    def _default_hashtags(self, package_type: PackageType) -> list[str]:
        base = ["#SFC", "#SaudiFootball", "#الدوري_السعودي"]
        extras = {
            PackageType.YOUTUBE_SHORT: ["#Shorts", "#Football"],
            PackageType.YOUTUBE_VIDEO: ["#YouTube", "#SPL"],
            PackageType.INSTAGRAM: ["#Reels", "#Football"],
            PackageType.TIKTOK: ["#TikTok", "#Football", "#viral"],
            PackageType.PODCAST: ["#Podcast", "#SportsRadio"],
            PackageType.X_THREAD: ["#Thread", "#SPL"],
        }
        return base + extras.get(package_type, [])

    async def _generate_caption(self, title: str, package_type: PackageType) -> str:
        if self.gateway:
            try:
                from sfc.ai.model_gateway import ModelRequest
                result = await self.gateway.complete(
                    ModelRequest(
                        prompt=(
                            f"Write a {package_type.value} social media caption (1-2 lines) for: '{title}'. "
                            "SFC Saudi football. Arabic-first, include emoji."
                        ),
                        max_tokens=80,
                    )
                )
                return result.content.strip()
            except Exception:
                pass
        return f"🔥 {title} | SFC — كرة القدم السعودية 🏆"

    # ------------------------------------------------------------------
    # Real-asset validation (Package 10B)
    # ------------------------------------------------------------------

    def validate_asset_for_packaging(
        self, asset: Any
    ) -> tuple[bool, list[str]]:
        """Validate a GeneratedAsset before including it in a content package.

        Accepts only assets where:
          - status == 'generated'
          - quality_score >= threshold
          - governance_status in ('approved', 'pending_review')
          - local_path is set and file exists with non-zero size
        """
        from sfc.creative.providers.generated_asset import (
            GeneratedAssetStatus,
            GovernanceStatus,
        )

        errors: list[str] = []

        # Status check
        if asset.status != GeneratedAssetStatus.GENERATED:
            errors.append(
                f"Asset status is '{asset.status.value}' — only 'generated' assets accepted"
            )

        # Quality check
        if asset.quality_score < self._QUALITY_THRESHOLD:
            errors.append(
                f"Quality score {asset.quality_score:.1f} below threshold {self._QUALITY_THRESHOLD}"
            )

        # Governance check
        if asset.governance_status not in (
            GovernanceStatus.APPROVED,
            GovernanceStatus.PENDING_REVIEW,
        ):
            errors.append(
                f"Governance status '{asset.governance_status.value}' not acceptable"
            )

        # File existence and size
        local_path = getattr(asset, "local_path", "")
        if not local_path:
            errors.append("No local_path — asset was not saved to disk")
        else:
            path = Path(local_path)
            if not path.exists():
                errors.append(f"File not found on disk: {local_path}")
            elif path.stat().st_size == 0:
                errors.append(f"File is zero bytes: {local_path}")

        # Checksum must be present
        if not getattr(asset, "checksum_sha256", ""):
            errors.append("No checksum — file integrity unverified")

        return (len(errors) == 0), errors

    async def package_from_generated_assets(
        self,
        package_type: "PackageType",
        title: str,
        generated_assets: list[Any],
        governance_cleared: bool = False,
    ) -> "ContentPackage":
        """Build a content package from validated GeneratedAsset objects.

        Only assets that pass validate_asset_for_packaging() are included.
        Raises ValueError if no valid assets are present.
        """
        valid_assets: list[Any] = []
        rejected_reasons: dict[str, list[str]] = {}
        for asset in generated_assets:
            ok, errors = self.validate_asset_for_packaging(asset)
            if ok:
                valid_assets.append(asset)
            else:
                rejected_reasons[getattr(asset, "asset_id", "unknown")] = errors

        if not valid_assets:
            raise ValueError(
                f"No valid GeneratedAssets for package '{title}'. "
                f"Rejections: {rejected_reasons}"
            )

        avg_quality = sum(a.quality_score for a in valid_assets) / len(valid_assets)
        media_assets = [a.to_dict() for a in valid_assets]

        return await self.create_package(
            package_type=package_type,
            title=title,
            media_assets=media_assets,
            quality_score=round(avg_quality, 1),
            governance_cleared=governance_cleared,
        )

    def get_ready_packages(self) -> list[ContentPackage]:
        return [p for p in self._packages if p.ready_to_publish]

    def get_recent_packages(self, limit: int = 20) -> list[ContentPackage]:
        return self._packages[-limit:]
