"""Clip Governance Layer — rights, brand safety, content policy, quality gate."""

from __future__ import annotations

import logging

from sfc.video_intelligence.governance.models import (
    ClipGovernanceResult,
    ClipGovernanceStatus,
)
from sfc.video_intelligence.ingestion.models import RightsStatus
from sfc.video_intelligence.packaging.models import ClipPackage
from sfc.video_intelligence.shared.constants import (
    CLIP_QUALITY_THRESHOLD,
    is_video_processing_enabled,
)

logger = logging.getLogger("sfc.video_intelligence.governance")

_singleton: "ClipGovernanceLayer | None" = None

_BRAND_UNSAFE_KEYWORDS = [
    "violence", "explicit", "adult", "hate", "discrimination",
    "عنف", "محتوى بالغ",
]


def get_clip_governance_layer() -> "ClipGovernanceLayer":
    global _singleton
    if _singleton is None:
        _singleton = ClipGovernanceLayer()
    return _singleton


class ClipGovernanceLayer:
    """Validates clips for rights, brand safety, content policy, and quality."""

    async def review(
        self,
        package: ClipPackage,
        rights_status: RightsStatus,
    ) -> ClipGovernanceResult:
        result = ClipGovernanceResult(
            clip_id=package.clip_id,
            package_id=package.package_id,
        )
        issues: list[str] = []

        # Rights gate
        if rights_status == RightsStatus.RESTRICTED:
            result.status = ClipGovernanceStatus.RIGHTS_BLOCKED
            result.rights_verified = False
            issues.append("Source rights are RESTRICTED — publishing blocked")
            result.issues = issues
            logger.warning("[Governance] Rights blocked: clip_id=%s", package.clip_id)
            return result

        result.rights_verified = rights_status in (
            RightsStatus.OWNED,
            RightsStatus.LICENSED,
            RightsStatus.PUBLIC_SOURCE,
        )
        if not result.rights_verified:
            issues.append(
                f"Rights status '{rights_status.value}' — publishing requires operator approval"
            )

        # Brand safety
        unsafe = self._check_brand_safety(package)
        result.brand_safe = not unsafe
        if unsafe:
            issues.extend(unsafe)

        # Content policy
        policy_issues = self._check_content_policy(package)
        result.content_policy_compliant = not policy_issues
        if policy_issues:
            issues.extend(policy_issues)

        # Quality gate
        result.quality_gate_passed = package.quality_score >= CLIP_QUALITY_THRESHOLD
        if not result.quality_gate_passed:
            issues.append(
                f"Quality score {package.quality_score:.1f} below threshold {CLIP_QUALITY_THRESHOLD}"
            )

        # Determine final status
        result.issues = issues
        if issues:
            if rights_status == RightsStatus.UNKNOWN or not result.rights_verified:
                result.status = ClipGovernanceStatus.NEEDS_MANUAL_REVIEW
            elif result.brand_safe and result.content_policy_compliant and result.quality_gate_passed:
                result.status = ClipGovernanceStatus.APPROVED
            else:
                result.status = ClipGovernanceStatus.REJECTED
        else:
            result.status = ClipGovernanceStatus.APPROVED

        logger.info(
            "[Governance] clip_id=%s status=%s issues=%d",
            package.clip_id,
            result.status.value,
            len(issues),
        )
        return result

    def _check_brand_safety(self, package: ClipPackage) -> list[str]:
        text = f"{package.title} {package.description}".lower()
        return [
            f"Brand safety flag: '{kw}'"
            for kw in _BRAND_UNSAFE_KEYWORDS
            if kw in text
        ]

    def _check_content_policy(self, package: ClipPackage) -> list[str]:
        issues = []
        if not package.title:
            issues.append("Package has no title")
        if not package.variants:
            issues.append("Package has no clip variants")
        return issues
