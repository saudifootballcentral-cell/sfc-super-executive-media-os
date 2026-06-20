"""Analytics Division — tracks and reports on all success metrics."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from core.models import Division, Platform, SFCEvent, SuccessMetrics
from divisions.base import BaseDivision


class AnalyticsDivision(BaseDivision):
    """Measures performance against success metrics defined in the constitution.

    Tracks: Reach, Watch Time, Retention, Engagement, Followers,
    Subscribers, Revenue, Authority, Share of Voice.
    """

    division = Division.ANALYTICS

    async def handle_event(self, event: SFCEvent) -> dict[str, Any] | None:
        return None

    def record_metrics(self, metrics: SuccessMetrics) -> None:
        key = f"metrics:{metrics.platform or 'all'}:{metrics.period_start.date().isoformat()}"
        self.memory.set(key, metrics.model_dump(mode="json"))
        self.logger.info(
            "[Analytics] Recorded metrics — reach=%d engagement=%.2f%%",
            metrics.reach,
            metrics.engagement_rate * 100,
        )

    def record_content_performance(
        self,
        content_id: str,
        platform: Platform,
        reach: int,
        engagement_rate: float,
        watch_time_seconds: int = 0,
        retention_rate: float = 0.0,
    ) -> dict[str, Any]:
        record = {
            "content_id": content_id,
            "platform": platform.value if isinstance(platform, Platform) else platform,
            "reach": reach,
            "engagement_rate": engagement_rate,
            "watch_time_seconds": watch_time_seconds,
            "retention_rate": retention_rate,
            "recorded_at": datetime.utcnow().isoformat(),
        }
        self.memory.set(f"perf:{content_id}:{record['platform']}", record)
        return record

    def get_top_content(self, n: int = 10) -> list[dict[str, Any]]:
        perf_keys = [k for k in self.memory.keys() if k.startswith("perf:")]
        records = [self.memory.get(k) for k in perf_keys]
        return sorted(records, key=lambda r: r.get("reach", 0), reverse=True)[:n]

    def aggregate_period(self, days: int = 7) -> dict[str, Any]:
        perf_keys = [k for k in self.memory.keys() if k.startswith("perf:")]
        records = [self.memory.get(k) for k in perf_keys]

        if not records:
            return {"period_days": days, "total_reach": 0, "avg_engagement": 0.0}

        total_reach = sum(r.get("reach", 0) for r in records)
        avg_engagement = sum(r.get("engagement_rate", 0) for r in records) / len(records)
        total_watch = sum(r.get("watch_time_seconds", 0) for r in records)

        return {
            "period_days": days,
            "content_count": len(records),
            "total_reach": total_reach,
            "avg_engagement_rate": avg_engagement,
            "total_watch_time_seconds": total_watch,
        }

    def platform_breakdown(self) -> dict[str, dict[str, Any]]:
        perf_keys = [k for k in self.memory.keys() if k.startswith("perf:")]
        breakdown: dict[str, dict[str, Any]] = {}

        for key in perf_keys:
            record = self.memory.get(key, {})
            platform = record.get("platform", "unknown")
            if platform not in breakdown:
                breakdown[platform] = {"reach": 0, "count": 0, "total_engagement": 0.0}
            breakdown[platform]["reach"] += record.get("reach", 0)
            breakdown[platform]["count"] += 1
            breakdown[platform]["total_engagement"] += record.get("engagement_rate", 0.0)

        for platform, data in breakdown.items():
            count = data["count"] or 1
            data["avg_engagement"] = data.pop("total_engagement") / count

        return breakdown
