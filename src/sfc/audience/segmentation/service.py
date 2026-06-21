"""Audience Segmentation Engine — identifies and analyzes audience clusters."""

from __future__ import annotations

import logging
import random
from typing import Any

from sfc.audience.segmentation.models import (
    AudienceCluster,
    AudienceSegment,
    AudienceSegmentReport,
    SegmentMetrics,
)

logger = logging.getLogger("sfc.audience.segmentation")

_singleton: "AudienceSegmentationEngine | None" = None


def get_segmentation_engine() -> "AudienceSegmentationEngine":
    global _singleton
    if _singleton is None:
        _singleton = AudienceSegmentationEngine()
    return _singleton


class AudienceSegmentationEngine:
    """Identifies and analyzes distinct audience clusters for targeting."""

    def __init__(self) -> None:
        self._gateway = None
        self._segments: dict[str, AudienceSegment] = {}
        self._history: list[AudienceSegmentReport] = []
        self._max_history = 200

    @property
    def gateway(self):
        if self._gateway is None:
            from sfc.ai.model_gateway import get_ai_gateway
            self._gateway = get_ai_gateway()
        return self._gateway

    async def segment(
        self,
        clusters: list[AudienceCluster] | None = None,
        context: dict[str, Any] | None = None,
    ) -> list[AudienceSegment]:
        """Segment audience into clusters with metrics and recommendations."""
        clusters = clusters or list(AudienceCluster)
        segments: list[AudienceSegment] = []

        for cluster in clusters:
            segment = self._build_segment(cluster, context or {})
            self._segments[segment.segment_id] = segment
            segments.append(segment)

        return segments

    async def generate_report(
        self, segments: list[AudienceSegment] | None = None
    ) -> AudienceSegmentReport:
        """Generate a comprehensive segmentation report."""
        if segments is None:
            segments = list(self._segments.values())
        if not segments:
            segments = await self.segment()

        total = sum(s.metrics.size for s in segments)
        fastest = max(segments, key=lambda s: s.metrics.monthly_growth_rate, default=None)
        highest_eng = max(segments, key=lambda s: s.metrics.engagement_rate, default=None)

        all_growth_opps = []
        all_targeting = []
        for s in segments:
            all_growth_opps.extend(s.growth_opportunities[:1])
            all_targeting.extend(s.targeting_recommendations[:1])

        ai_insights = await self._get_ai_insights(segments, total)

        report = AudienceSegmentReport(
            segments=segments,
            total_audience=total,
            fastest_growing=fastest.cluster if fastest else None,
            highest_engagement=highest_eng.cluster if highest_eng else None,
            growth_opportunities=all_growth_opps[:6],
            targeting_recommendations=all_targeting[:6],
            ai_insights=ai_insights,
        )

        if len(self._history) < self._max_history:
            self._history.append(report)

        return report

    def get_segment(self, segment_id: str) -> AudienceSegment | None:
        return self._segments.get(segment_id)

    def get_history(self, limit: int = 20) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self._history[-limit:]]

    def _build_segment(
        self, cluster: AudienceCluster, context: dict[str, Any]
    ) -> AudienceSegment:
        configs = {
            AudienceCluster.HARDCORE_FANS: (900_000, 0.15, 85, 0.92, 4.5),
            AudienceCluster.CASUAL_FANS: (3_200_000, 0.04, 45, 0.55, 12.0),
            AudienceCluster.MATCH_DAY_FANS: (1_800_000, 0.08, 65, 0.60, 8.0),
            AudienceCluster.TRANSFER_FOLLOWERS: (750_000, 0.12, 72, 0.70, 20.0),
            AudienceCluster.NATIONAL_TEAM_FANS: (2_400_000, 0.09, 70, 0.75, 7.0),
            AudienceCluster.TACTICAL_ENTHUSIASTS: (380_000, 0.18, 88, 0.85, 5.0),
            AudienceCluster.MEDIA_FOLLOWERS: (220_000, 0.22, 80, 0.65, 6.0),
            AudienceCluster.SPONSOR_FOLLOWERS: (180_000, 0.06, 40, 0.50, 3.0),
        }

        base_size, base_eng, influence, retention, growth = configs.get(
            cluster, (100_000, 0.05, 50, 0.60, 5.0)
        )
        size = int(base_size * random.uniform(0.88, 1.12))
        engagement = round(base_eng * random.uniform(0.8, 1.2) * 100, 1)

        metrics = SegmentMetrics(
            size=size,
            engagement_rate=engagement,
            influence_score=round(influence * random.uniform(0.9, 1.1), 1),
            retention_rate=round(retention * 100 * random.uniform(0.95, 1.05), 1),
            monthly_growth_rate=round(growth * random.uniform(0.8, 1.3), 1),
            avg_session_minutes=round(random.uniform(4, 20), 1),
            content_consumption_per_day=round(random.uniform(2, 8), 1),
            churn_risk=round(100 - retention * 100, 1),
        )

        sensitivity = {
            "player": random.uniform(0.5, 0.9),
            "transfer": random.uniform(0.6, 0.95),
            "national_team": random.uniform(0.4, 0.85),
        }

        growth_opps = [
            f"Grow {cluster.value.replace('_', ' ')} via TikTok-first content",
            f"Increase {cluster.value.replace('_', ' ')} retention through exclusive content",
        ]
        targeting = [
            f"Target {cluster.value.replace('_', ' ')} at peak hours 20-22 UTC",
            f"Use short-form video for {cluster.value.replace('_', ' ')} engagement",
        ]

        return AudienceSegment(
            cluster=cluster,
            name=cluster.value.replace("_", " ").title(),
            description=f"Saudi football {cluster.value.replace('_', ' ')} audience cluster",
            metrics=metrics,
            primary_platforms=["x", "instagram", "tiktok"],
            content_preferences=["match highlights", "player content", "transfer news"],
            narrative_sensitivity=sensitivity,
            peak_hours=[20, 21, 22, 9],
            growth_opportunities=growth_opps,
            targeting_recommendations=targeting,
        )

    async def _get_ai_insights(
        self, segments: list[AudienceSegment], total: int
    ) -> str:
        try:
            from sfc.ai.models import ModelRequest
            fastest = max(segments, key=lambda s: s.metrics.monthly_growth_rate, default=None)
            req = ModelRequest(
                prompt=f"Saudi football segmentation: {total:,} total, fastest growing: {fastest.name if fastest else 'N/A'}",
                task_type="audience_segmentation",
                max_tokens=200,
            )
            resp = await self.gateway.complete(req)
            return resp.content
        except Exception:
            fastest = max(segments, key=lambda s: s.metrics.monthly_growth_rate, default=None)
            return (
                f"Segmented {total:,} total audience across {len(segments)} clusters. "
                f"Fastest growing: {fastest.name if fastest else 'N/A'} "
                f"({fastest.metrics.monthly_growth_rate:.1f}%/month)."
            )
