"""Tests for Clip Governance Layer."""

from __future__ import annotations

import pytest

from sfc.video_intelligence.governance.models import ClipGovernanceStatus
from sfc.video_intelligence.governance.service import ClipGovernanceLayer
from sfc.video_intelligence.ingestion.models import RightsStatus
from sfc.video_intelligence.packaging.models import ClipPackage, PlatformClipVariant


def _package(
    title: str = "SFC Match Highlights",
    quality_score: float = 80.0,
    has_variant: bool = True,
) -> ClipPackage:
    variants = []
    if has_variant:
        variants.append(
            PlatformClipVariant(
                platform="youtube_short",
                aspect_ratio="9:16",
                duration_seconds=30.0,
                ready_to_publish=True,
            )
        )
    return ClipPackage(
        clip_id="clip-1",
        video_id="vid-1",
        title=title,
        quality_score=quality_score,
        variants=variants,
    )


class TestGovernanceRightsGating:
    @pytest.mark.asyncio
    async def test_restricted_rights_blocks_publishing(self):
        svc = ClipGovernanceLayer()
        result = await svc.review(_package(), RightsStatus.RESTRICTED)
        assert result.status == ClipGovernanceStatus.RIGHTS_BLOCKED
        assert result.cleared_for_publishing is False

    @pytest.mark.asyncio
    async def test_owned_rights_verified(self):
        svc = ClipGovernanceLayer()
        result = await svc.review(_package(), RightsStatus.OWNED)
        assert result.rights_verified is True

    @pytest.mark.asyncio
    async def test_unknown_rights_needs_manual_review(self):
        svc = ClipGovernanceLayer()
        result = await svc.review(_package(), RightsStatus.UNKNOWN)
        assert result.status == ClipGovernanceStatus.NEEDS_MANUAL_REVIEW

    @pytest.mark.asyncio
    async def test_unknown_rights_not_cleared_for_publishing(self):
        svc = ClipGovernanceLayer()
        result = await svc.review(_package(), RightsStatus.UNKNOWN)
        assert result.cleared_for_publishing is False

    @pytest.mark.asyncio
    async def test_licensed_rights_approved(self):
        svc = ClipGovernanceLayer()
        result = await svc.review(_package(quality_score=85.0), RightsStatus.LICENSED)
        assert result.status == ClipGovernanceStatus.APPROVED
        assert result.cleared_for_publishing is True


class TestGovernanceQualityGate:
    @pytest.mark.asyncio
    async def test_low_quality_score_fails_gate(self):
        svc = ClipGovernanceLayer()
        result = await svc.review(_package(quality_score=50.0), RightsStatus.OWNED)
        assert result.quality_gate_passed is False
        assert any("Quality" in issue for issue in result.issues)

    @pytest.mark.asyncio
    async def test_high_quality_score_passes_gate(self):
        svc = ClipGovernanceLayer()
        result = await svc.review(_package(quality_score=90.0), RightsStatus.OWNED)
        assert result.quality_gate_passed is True


class TestGovernanceBrandSafety:
    @pytest.mark.asyncio
    async def test_brand_safe_content_approved(self):
        svc = ClipGovernanceLayer()
        result = await svc.review(_package(title="SFC Goal Highlights"), RightsStatus.OWNED)
        assert result.brand_safe is True

    @pytest.mark.asyncio
    async def test_brand_unsafe_keyword_flagged(self):
        svc = ClipGovernanceLayer()
        result = await svc.review(
            _package(title="violence at the match"), RightsStatus.OWNED
        )
        assert result.brand_safe is False
        assert any("Brand safety" in issue for issue in result.issues)


class TestGovernanceContentPolicy:
    @pytest.mark.asyncio
    async def test_package_without_title_fails_policy(self):
        svc = ClipGovernanceLayer()
        result = await svc.review(_package(title=""), RightsStatus.OWNED)
        assert result.content_policy_compliant is False

    @pytest.mark.asyncio
    async def test_package_without_variants_fails_policy(self):
        svc = ClipGovernanceLayer()
        result = await svc.review(_package(has_variant=False), RightsStatus.OWNED)
        assert result.content_policy_compliant is False

    @pytest.mark.asyncio
    async def test_full_approval_path(self):
        svc = ClipGovernanceLayer()
        result = await svc.review(
            _package(title="SFC Highlights", quality_score=90.0, has_variant=True),
            RightsStatus.OWNED,
        )
        assert result.status == ClipGovernanceStatus.APPROVED
        assert result.cleared_for_publishing is True
        assert result.issues == []
