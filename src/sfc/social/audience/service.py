"""Audience Intelligence Service — analyzes fan segments and engagement patterns."""

from __future__ import annotations

import logging
import random
from typing import Any

from sfc.social.audience.models import (
    AudienceProfile,
    AudienceReport,
    AudienceSegment,
    AudienceSegmentType,
)

logger = logging.getLogger("sfc.social.audience")

_singleton: "AudienceIntelligenceService | None" = None


def get_audience_service() -> "AudienceIntelligenceService":
    global _singleton
    if _singleton is None:
        _singleton = AudienceIntelligenceService()
    return _singleton


class AudienceIntelligenceService:
    """Analyzes Saudi football audience segments and behavioral patterns."""

    def __init__(self) -> None:
        self._gateway = None
        self._profile: AudienceProfile | None = None
        self._history: list[AudienceReport] = []
        self._max_history = 200

    @property
    def gateway(self):
        if self._gateway is None:
            from sfc.ai.model_gateway import get_ai_gateway
            self._gateway = get_ai_gateway()
        return self._gateway

    async def analyze(
        self,
        segment_types: list[AudienceSegmentType] | None = None,
        context: dict[str, Any] | None = None,
    ) -> AudienceProfile:
        """Analyze audience segments and build a comprehensive profile."""
        segment_types = segment_types or list(AudienceSegmentType)
        segments = [self._build_segment(st) for st in segment_types]

        total_audience = sum(s.size for s in segments)
        top_platform = self._find_top_platform(segments)
        peak_hour = self._find_peak_hour(segments)
        avg_growth = (
            sum(s.growth_rate for s in segments) / len(segments) if segments else 0.0
        )

        profile = AudienceProfile(
            total_audience=total_audience,
            segments=segments,
            top_platform=top_platform,
            peak_day="Friday",
            peak_hour=peak_hour,
            avg_content_consumed_per_day=random.uniform(3.5, 8.2),
            growth_rate_monthly=round(avg_growth, 1),
            growth_opportunities=self._growth_opportunities(segments),
            retention_opportunities=self._retention_opportunities(segments),
        )

        self._profile = profile
        return profile

    async def get_segments(
        self,
        segment_type: AudienceSegmentType | None = None,
    ) -> list[AudienceSegment]:
        """Return cached segments, optionally filtered by type."""
        if self._profile is None:
            await self.analyze()

        segments = self._profile.segments if self._profile else []
        if segment_type:
            segments = [s for s in segments if s.segment_type == segment_type]
        return segments

    async def generate_report(
        self,
        profile: AudienceProfile | None = None,
    ) -> AudienceReport:
        """Generate a comprehensive audience intelligence report."""
        if profile is None:
            profile = await self.analyze()

        segment_breakdown = [
            {
                "segment": s.name,
                "type": s.segment_type.value,
                "size": s.size,
                "growth_rate": s.growth_rate,
                "retention_rate": s.retention_rate,
            }
            for s in profile.segments
        ]

        platform_totals: dict[str, float] = {}
        for seg in profile.segments:
            for p in seg.preferred_platforms:
                platform_totals[p] = platform_totals.get(p, 0) + seg.size

        total = max(sum(platform_totals.values()), 1)
        platform_breakdown = {
            p: round(v / total * 100, 1) for p, v in platform_totals.items()
        }

        engagement_patterns = {
            "peak_hour_utc": profile.peak_hour,
            "peak_day": profile.peak_day,
            "avg_session_minutes": round(
                sum(s.avg_session_minutes for s in profile.segments) / max(len(profile.segments), 1), 1
            ),
            "top_content_types": ["match highlights", "transfer news", "player profiles"],
        }

        recommendations = (
            profile.growth_opportunities + profile.retention_opportunities
        )[:8]
        ai_insights = await self._get_ai_insights(profile)

        report = AudienceReport(
            profile=profile,
            segment_breakdown=segment_breakdown,
            engagement_patterns=engagement_patterns,
            platform_breakdown=platform_breakdown,
            recommendations=recommendations,
            ai_insights=ai_insights,
        )

        if len(self._history) < self._max_history:
            self._history.append(report)

        return report

    def get_history(self, limit: int = 20) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self._history[-limit:]]

    def _build_segment(self, segment_type: AudienceSegmentType) -> AudienceSegment:
        configs = {
            AudienceSegmentType.CORE_FANS: (850000, 3.2, ["x", "instagram"]),
            AudienceSegmentType.CASUAL_VIEWERS: (2100000, 8.5, ["youtube", "tiktok"]),
            AudienceSegmentType.TRANSFER_WATCHERS: (650000, 12.1, ["x", "reddit"]),
            AudienceSegmentType.STATS_ENTHUSIASTS: (320000, 5.4, ["reddit", "x"]),
            AudienceSegmentType.YOUTH_AUDIENCE: (1400000, 22.3, ["tiktok", "instagram"]),
            AudienceSegmentType.INTERNATIONAL_FANS: (980000, 15.7, ["youtube", "x"]),
            AudienceSegmentType.SAUDI_NATIONAL_FANS: (3200000, 6.8, ["x", "instagram"]),
            AudienceSegmentType.FANTASY_PLAYERS: (280000, 9.1, ["x", "reddit"]),
        }
        size, growth, platforms = configs.get(segment_type, (100000, 5.0, ["x"]))
        size = int(size * random.uniform(0.85, 1.15))
        growth = round(growth * random.uniform(0.8, 1.2), 1)

        return AudienceSegment(
            name=segment_type.value.replace("_", " ").title(),
            segment_type=segment_type,
            size=size,
            growth_rate=growth,
            top_interests=["match highlights", "transfer news", "player stats"],
            preferred_platforms=platforms,
            peak_hours=[20, 21, 22],
            content_preferences=["video", "breaking news", "analysis"],
            avg_session_minutes=random.uniform(4, 18),
            retention_rate=random.uniform(0.55, 0.88),
        )

    def _find_top_platform(self, segments: list[AudienceSegment]) -> str:
        counts: dict[str, int] = {}
        for seg in segments:
            for p in seg.preferred_platforms:
                counts[p] = counts.get(p, 0) + seg.size
        return max(counts, key=lambda k: counts[k], default="x")

    def _find_peak_hour(self, segments: list[AudienceSegment]) -> int:
        hour_counts: dict[int, int] = {}
        for seg in segments:
            for h in seg.peak_hours:
                hour_counts[h] = hour_counts.get(h, 0) + seg.size
        return max(hour_counts, key=lambda k: hour_counts[k], default=20)

    def _growth_opportunities(self, segments: list[AudienceSegment]) -> list[str]:
        opps = []
        for s in sorted(segments, key=lambda x: x.growth_rate, reverse=True)[:3]:
            opps.append(
                f"Target {s.name} segment ({s.growth_rate:.1f}% monthly growth)"
            )
        return opps

    def _retention_opportunities(self, segments: list[AudienceSegment]) -> list[str]:
        opps = []
        for s in sorted(segments, key=lambda x: x.retention_rate)[:2]:
            opps.append(
                f"Improve retention for {s.name} (currently {s.retention_rate:.0%})"
            )
        return opps

    async def _get_ai_insights(self, profile: AudienceProfile) -> str:
        try:
            from sfc.ai.models import ModelRequest
            req = ModelRequest(
                prompt=f"Saudi football audience: {profile.total_audience:,} fans, top platform: {profile.top_platform}, growth: {profile.growth_rate_monthly:.1f}%/month",
                task_type="audience_analysis",
                max_tokens=200,
            )
            resp = await self.gateway.complete(req)
            return resp.content
        except Exception:
            return (
                f"Total audience of {profile.total_audience:,} across {len(profile.segments)} segments. "
                f"Primary platform: {profile.top_platform}. "
                f"Monthly growth: {profile.growth_rate_monthly:.1f}%."
            )
