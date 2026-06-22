"""Analytics report generator — Hourly, Daily, Weekly, Monthly, Quarterly."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

from sfc.analytics_sync.aggregation.models import AggregatedPerformance, UnifiedAnalyticsRecord

logger = logging.getLogger("sfc.analytics_sync.reporting")


class AnalyticsReport:
    """Structured analytics report for a given period."""

    def __init__(
        self,
        period: str,
        run_id: str,
        records: list[UnifiedAnalyticsRecord],
        aggregations: dict[str, list[AggregatedPerformance]],
    ) -> None:
        self.report_id = str(uuid4())
        self.period = period
        self.run_id = run_id
        self.generated_at = datetime.utcnow()
        self.records = records
        self.aggregations = aggregations
        self.summary = self._build_summary()

    def _build_summary(self) -> dict[str, Any]:
        total_views = sum(r.views for r in self.records)
        total_impressions = sum(r.impressions for r in self.records)
        total_likes = sum(r.likes for r in self.records)
        total_shares = sum(r.shares for r in self.records)
        total_comments = sum(r.comments for r in self.records)
        eng_rates = [r.engagement_rate for r in self.records if r.engagement_rate > 0]
        avg_eng = round(sum(eng_rates) / len(eng_rates), 4) if eng_rates else 0.0
        top = max(self.records, key=lambda r: r.views, default=None)
        platforms = list({r.platform.value for r in self.records})
        return {
            "period": self.period,
            "total_records": len(self.records),
            "platforms": platforms,
            "total_views": total_views,
            "total_impressions": total_impressions,
            "total_likes": total_likes,
            "total_shares": total_shares,
            "total_comments": total_comments,
            "avg_engagement_rate": avg_eng,
            "top_content_id": top.content_id if top else "",
            "top_content_views": top.views if top else 0,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "period": self.period,
            "run_id": self.run_id,
            "generated_at": self.generated_at.isoformat(),
            "summary": self.summary,
            "aggregations": {
                dim: [a.to_dict() for a in aggs]
                for dim, aggs in self.aggregations.items()
            },
            "record_count": len(self.records),
        }


class ReportGenerator:
    """Generates analytics reports for different time periods."""

    def generate(
        self,
        period: str,
        records: list[UnifiedAnalyticsRecord],
        aggregations: dict[str, list[AggregatedPerformance]],
        run_id: str = "",
    ) -> AnalyticsReport:
        """Generate a report for the given period."""
        if period not in ("hourly", "daily", "weekly", "monthly", "quarterly"):
            raise ValueError(f"Unknown period: {period!r}")
        report = AnalyticsReport(period=period, run_id=run_id, records=records, aggregations=aggregations)
        logger.info(
            "[Reporting] %s report generated: %d records, total_views=%d",
            period, len(records), report.summary.get("total_views", 0),
        )
        return report

    def generate_top_performers(
        self,
        records: list[UnifiedAnalyticsRecord],
        top_n: int = 10,
        metric: str = "views",
    ) -> list[UnifiedAnalyticsRecord]:
        """Return top N records sorted by the given metric."""
        return sorted(records, key=lambda r: getattr(r, metric, 0), reverse=True)[:top_n]

    def generate_optimization_suggestions(
        self,
        aggregations: dict[str, list[AggregatedPerformance]],
    ) -> list[str]:
        """Generate human-readable optimization suggestions from aggregated data."""
        suggestions: list[str] = []
        platform_aggs = aggregations.get("platform", [])
        if platform_aggs:
            best = max(platform_aggs, key=lambda a: a.avg_engagement_rate, default=None)
            worst = min(platform_aggs, key=lambda a: a.avg_engagement_rate, default=None)
            if best and best.avg_engagement_rate > 0:
                suggestions.append(f"Best performing platform: {best.dimension_value} ({best.avg_engagement_rate:.2f}% engagement)")
            if worst and best and worst.dimension_value != best.dimension_value:
                suggestions.append(f"Underperforming platform: {worst.dimension_value} — consider reducing posting frequency")

        content_aggs = aggregations.get("content_type", [])
        if content_aggs:
            best_type = max(content_aggs, key=lambda a: a.avg_engagement_rate, default=None)
            if best_type and best_type.avg_engagement_rate > 0:
                suggestions.append(f"Highest engagement content type: {best_type.dimension_value}")

        return suggestions


_singleton: ReportGenerator | None = None


def get_report_generator() -> ReportGenerator:
    global _singleton
    if _singleton is None:
        _singleton = ReportGenerator()
    return _singleton
