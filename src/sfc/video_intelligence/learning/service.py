"""Clip Learning Loop — tracks performance and refines detection weights."""

from __future__ import annotations

import logging
from collections import defaultdict

from sfc.video_intelligence.learning.models import (
    ClipPerformanceRecord,
    LearningInsight,
    LearningReport,
)
from sfc.video_intelligence.packaging.models import ClipPackage
from sfc.video_intelligence.scoring.models import ClipScore
from sfc.video_intelligence.shared.constants import EVENT_HIGHLIGHT_WEIGHTS

logger = logging.getLogger("sfc.video_intelligence.learning")

_singleton: "ClipLearningLoop | None" = None


def get_clip_learning_loop() -> "ClipLearningLoop":
    global _singleton
    if _singleton is None:
        _singleton = ClipLearningLoop()
    return _singleton


class ClipLearningLoop:
    """Records clip performance and derives weight adjustments for future scoring."""

    def __init__(self) -> None:
        self._records: list[ClipPerformanceRecord] = []
        self._adjusted_weights: dict[str, float] = dict(EVENT_HIGHLIGHT_WEIGHTS)

    def record_prediction(
        self, package: ClipPackage, score: ClipScore
    ) -> ClipPerformanceRecord:
        record = ClipPerformanceRecord(
            clip_id=package.clip_id,
            platform=package.variants[0].platform if package.variants else "unknown",
            clip_type=package.clip_type,
            predicted_score=score.overall_score,
        )
        self._records.append(record)
        return record

    def record_performance(
        self,
        clip_id: str,
        platform: str,
        views: int,
        likes: int,
        shares: int,
        comments: int,
        watch_time_seconds: float = 0.0,
    ) -> ClipPerformanceRecord:
        total_interactions = likes + shares + comments
        engagement_rate = (total_interactions / max(views, 1)) * 100
        viral_score = min(100.0, (shares * 3 + likes * 1 + comments * 2) / max(views, 1) * 1000)

        record = ClipPerformanceRecord(
            clip_id=clip_id,
            platform=platform,
            views=views,
            likes=likes,
            shares=shares,
            comments=comments,
            watch_time_seconds=watch_time_seconds,
            engagement_rate=round(engagement_rate, 2),
            viral_score=round(viral_score, 1),
        )
        # Update existing prediction record if it exists
        existing = next((r for r in self._records if r.clip_id == clip_id), None)
        if existing:
            existing.views = views
            existing.likes = likes
            existing.shares = shares
            existing.comments = comments
            existing.engagement_rate = record.engagement_rate
            existing.viral_score = record.viral_score
            existing.prediction_error = abs(existing.predicted_score - viral_score)
            return existing

        self._records.append(record)
        return record

    async def generate_report(self) -> LearningReport:
        report = LearningReport(total_clips_tracked=len(self._records))

        if not self._records:
            return report

        # Engagement stats
        total_eng = sum(r.engagement_rate for r in self._records)
        report.avg_engagement_rate = round(
            total_eng / max(len(self._records), 1), 2
        )

        # Top clip type by avg engagement
        by_type: dict[str, list[float]] = defaultdict(list)
        by_platform: dict[str, list[float]] = defaultdict(list)
        for r in self._records:
            if r.clip_type:
                by_type[r.clip_type].append(r.engagement_rate)
            if r.platform:
                by_platform[r.platform].append(r.engagement_rate)

        if by_type:
            report.top_clip_type = max(
                by_type, key=lambda k: sum(by_type[k]) / len(by_type[k])
            )
        if by_platform:
            report.top_platform = max(
                by_platform, key=lambda k: sum(by_platform[k]) / len(by_platform[k])
            )

        # Generate insights
        insights = []
        if report.top_clip_type:
            avg = sum(by_type[report.top_clip_type]) / len(by_type[report.top_clip_type])
            insights.append(
                LearningInsight(
                    insight_type="clip_type_performance",
                    description=f"'{report.top_clip_type}' clips have highest avg engagement ({avg:.1f}%)",
                    confidence=0.85,
                    action_recommendation=f"Prioritize '{report.top_clip_type}' clips in future extraction",
                    data={"clip_type": report.top_clip_type, "avg_engagement": avg},
                )
            )
        if report.top_platform:
            avg = sum(by_platform[report.top_platform]) / len(by_platform[report.top_platform])
            insights.append(
                LearningInsight(
                    insight_type="platform_performance",
                    description=f"'{report.top_platform}' delivers highest avg engagement ({avg:.1f}%)",
                    confidence=0.80,
                    action_recommendation=f"Prioritize '{report.top_platform}' for clip packaging",
                    data={"platform": report.top_platform, "avg_engagement": avg},
                )
            )

        # Weight adjustments for event detection
        weight_adjustments: dict[str, float] = {}
        for clip_type, engagements in by_type.items():
            if clip_type in self._adjusted_weights:
                avg_eng = sum(engagements) / len(engagements)
                current = self._adjusted_weights[clip_type]
                # Nudge weight by ±5% based on performance vs average
                if avg_eng > report.avg_engagement_rate:
                    new_weight = min(1.0, current * 1.05)
                else:
                    new_weight = max(0.1, current * 0.95)
                self._adjusted_weights[clip_type] = round(new_weight, 3)
                weight_adjustments[clip_type] = round(new_weight, 3)

        report.insights = insights
        report.weight_adjustments = weight_adjustments
        logger.info(
            "[Learning] Report generated: clips=%d top_type=%s top_platform=%s",
            report.total_clips_tracked,
            report.top_clip_type,
            report.top_platform,
        )
        return report

    def get_adjusted_weights(self) -> dict[str, float]:
        return dict(self._adjusted_weights)

    def get_records(self) -> list[ClipPerformanceRecord]:
        return list(self._records)

    def reset_for_test(self) -> None:
        self._records.clear()
        self._adjusted_weights = dict(EVENT_HIGHLIGHT_WEIGHTS)
