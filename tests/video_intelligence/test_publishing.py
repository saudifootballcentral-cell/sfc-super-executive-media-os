"""Tests for Clip Publishing Integration."""

from __future__ import annotations

import pytest

from sfc.video_intelligence.governance.models import ClipGovernanceResult, ClipGovernanceStatus
from sfc.video_intelligence.packaging.models import ClipPackage, PlatformClipVariant
from sfc.video_intelligence.publishing.service import ClipPublishingIntegration


def _package(platform: str = "youtube_short", quality: float = 85.0) -> ClipPackage:
    return ClipPackage(
        clip_id="clip-1",
        video_id="vid-1",
        title="SFC Goal Highlights",
        description="Amazing goal from Saudi Pro League",
        quality_score=quality,
        variants=[
            PlatformClipVariant(
                platform=platform,
                aspect_ratio="9:16",
                duration_seconds=30.0,
                ready_to_publish=True,
            )
        ],
    )


def _approved_governance() -> ClipGovernanceResult:
    return ClipGovernanceResult(
        clip_id="clip-1",
        package_id="pkg-1",
        status=ClipGovernanceStatus.APPROVED,
        rights_verified=True,
        brand_safe=True,
        content_policy_compliant=True,
        quality_gate_passed=True,
    )


def _blocked_governance() -> ClipGovernanceResult:
    return ClipGovernanceResult(
        clip_id="clip-1",
        package_id="pkg-1",
        status=ClipGovernanceStatus.RIGHTS_BLOCKED,
        rights_verified=False,
    )


class TestClipPublishing:
    @pytest.mark.asyncio
    async def test_blocked_governance_returns_blocked_status(self):
        svc = ClipPublishingIntegration()
        svc.reset_for_test()
        result = await svc.publish(_package(), _blocked_governance())
        assert result["status"] == "blocked"
        assert result["clip_id"] == "clip-1"

    @pytest.mark.asyncio
    async def test_approved_governance_submits_to_content_packaging(self):
        # x_video routes through ContentPackagingService (Buffer); youtube goes to YouTubeVideoPublisher
        svc = ClipPublishingIntegration()
        svc.reset_for_test()
        result = await svc.publish(_package(platform="x_video"), _approved_governance())
        assert result["status"] == "submitted"
        platform_result = result["platform_results"][0]
        assert "content_package_id" in platform_result

    @pytest.mark.asyncio
    async def test_published_record_stored(self):
        svc = ClipPublishingIntegration()
        svc.reset_for_test()
        await svc.publish(_package(), _approved_governance())
        assert len(svc.get_published()) == 1

    @pytest.mark.asyncio
    async def test_multiple_platforms_publish(self):
        svc = ClipPublishingIntegration()
        svc.reset_for_test()
        for platform in ("youtube_short", "instagram_reel", "tiktok"):
            pkg = _package(platform=platform)
            pkg.clip_id = f"clip-{platform}"
            gov = _approved_governance()
            gov.clip_id = pkg.clip_id
            await svc.publish(pkg, gov)
        assert len(svc.get_published()) == 3

    @pytest.mark.asyncio
    async def test_platform_maps_to_package_type(self):
        svc = ClipPublishingIntegration()
        from sfc.creative.packaging.models import PackageType
        assert svc._platform_to_package_type("youtube_short") == PackageType.YOUTUBE_SHORT
        assert svc._platform_to_package_type("instagram_reel") == PackageType.INSTAGRAM
        assert svc._platform_to_package_type("tiktok") == PackageType.TIKTOK
        assert svc._platform_to_package_type("x_video") == PackageType.X_THREAD

    @pytest.mark.asyncio
    async def test_needs_manual_review_is_blocked(self):
        svc = ClipPublishingIntegration()
        svc.reset_for_test()
        gov = ClipGovernanceResult(
            clip_id="clip-1",
            package_id="pkg-1",
            status=ClipGovernanceStatus.NEEDS_MANUAL_REVIEW,
            rights_verified=False,
            brand_safe=True,
            content_policy_compliant=True,
        )
        result = await svc.publish(_package(), gov)
        assert result["status"] == "blocked"
