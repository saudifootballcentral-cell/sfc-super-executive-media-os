"""Historical Analytics Service — trend tracking, growth analysis, historical comparison."""

from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta
from typing import Any

from sfc.analytics.historical.models import (
    HistoricalComparison,
    HistoricalDataPoint,
    MetricType,
    TrendDirection,
    TrendReport,
)

logger = logging.getLogger("sfc.analytics.historical.service")

_singleton: "HistoricalAnalyticsService | None" = None


def get_historical_service() -> "HistoricalAnalyticsService":
    global _singleton
    if _singleton is None:
        _singleton = HistoricalAnalyticsService()
    return _singleton


class HistoricalAnalyticsService:
    """In-process historical analytics store with trend analysis."""

    def __init__(self) -> None:
        self._data: list[HistoricalDataPoint] = []

    def record(self, point: HistoricalDataPoint) -> None:
        self._data.append(point)
        # Keep last 10,000 data points in memory
        if len(self._data) > 10_000:
            self._data = self._data[-10_000:]

    def record_from_state(self, state: dict[str, Any]) -> list[HistoricalDataPoint]:
        """Extract and store metrics from a completed pipeline state."""
        points: list[HistoricalDataPoint] = []
        analytics = state.get("analytics_report", {})
        revenue = analytics.get("revenue_summary", {})
        run_id = state.get("run_id", "")
        task_type = state.get("task_type", "")

        _metrics = [
            (MetricType.REACH, "estimated_reach", analytics, "views"),
            (MetricType.ENGAGEMENT, "estimated_engagement_rate", analytics, "%"),
            (MetricType.PUBLISHING, "content_pieces_published", analytics, "items"),
            (MetricType.REVENUE, "estimated_revenue_impact_usd", analytics, "USD"),
            (MetricType.REVENUE, "total_opportunity_usd", revenue, "USD"),
            (MetricType.GOVERNANCE, "approval_rate", analytics, "%"),
        ]
        for metric_type, key, source, unit in _metrics:
            if key in source:
                val = source[key]
                if isinstance(val, (int, float)):
                    p = HistoricalDataPoint(
                        metric_type=metric_type,
                        metric_name=key,
                        value=float(val),
                        unit=unit,
                        run_id=run_id,
                        task_type=task_type,
                    )
                    self.record(p)
                    points.append(p)

        try:
            from sfc.ai.cost_tracker import get_cost_tracker
            cost = get_cost_tracker().session_total_usd
            p = HistoricalDataPoint(
                metric_type=MetricType.AI_COST,
                metric_name="session_total_usd",
                value=cost,
                unit="USD",
                run_id=run_id,
                task_type=task_type,
            )
            self.record(p)
            points.append(p)
        except Exception:
            pass

        return points

    def get_trend(self, metric_name: str, period_days: int = 7) -> TrendReport | None:
        cutoff = datetime.utcnow() - timedelta(days=period_days)
        pts = [
            p for p in self._data
            if p.metric_name == metric_name and p.recorded_at >= cutoff
        ]
        if not pts:
            return None
        pts.sort(key=lambda p: p.recorded_at)
        values = [p.value for p in pts]
        first = values[0]
        last = values[-1]
        avg = sum(values) / len(values)
        std = math.sqrt(sum((v - avg) ** 2 for v in values) / len(values)) if len(values) > 1 else 0.0
        change_pct = ((last - first) / first * 100) if first != 0 else 0.0

        if abs(change_pct) < 2.0:
            direction = TrendDirection.STABLE
        elif change_pct > 0:
            direction = TrendDirection.UP
        else:
            direction = TrendDirection.DOWN
        if std > avg * 0.3:
            direction = TrendDirection.VOLATILE

        return TrendReport(
            metric_type=pts[0].metric_type,
            metric_name=metric_name,
            period_days=period_days,
            data_points=len(pts),
            first_value=first,
            last_value=last,
            min_value=min(values),
            max_value=max(values),
            avg_value=round(avg, 4),
            std_dev=round(std, 4),
            change_pct=round(change_pct, 2),
            direction=direction,
            trend_data=[
                {"ts": p.recorded_at.isoformat(), "value": p.value}
                for p in pts
            ],
        )

    def get_all_trends(self, period_days: int = 7) -> list[TrendReport]:
        metric_names = {p.metric_name for p in self._data}
        trends = []
        for name in metric_names:
            trend = self.get_trend(name, period_days)
            if trend:
                trends.append(trend)
        return trends

    def compare(
        self,
        metric_name: str,
        period_a_days: int = 7,
        period_b_days: int = 14,
    ) -> HistoricalComparison | None:
        now = datetime.utcnow()
        a_cutoff = now - timedelta(days=period_a_days)
        b_cutoff = now - timedelta(days=period_b_days)

        pts_a = [
            p for p in self._data
            if p.metric_name == metric_name and p.recorded_at >= a_cutoff
        ]
        pts_b = [
            p for p in self._data
            if p.metric_name == metric_name
            and b_cutoff <= p.recorded_at < a_cutoff
        ]
        if not pts_a or not pts_b:
            return None

        avg_a = sum(p.value for p in pts_a) / len(pts_a)
        avg_b = sum(p.value for p in pts_b) / len(pts_b)
        change_pct = ((avg_a - avg_b) / avg_b * 100) if avg_b != 0 else 0.0

        return HistoricalComparison(
            metric_name=metric_name,
            period_a_label=f"Last {period_a_days} days",
            period_a_avg=round(avg_a, 4),
            period_b_label=f"Prior {period_b_days - period_a_days} days",
            period_b_avg=round(avg_b, 4),
            change_pct=round(change_pct, 2),
            is_improvement=change_pct > 0,
        )

    def get_growth_report(self) -> dict[str, Any]:
        """Summarize growth across all tracked metrics."""
        trends = self.get_all_trends(period_days=7)
        improvements = [t for t in trends if t.direction == TrendDirection.UP]
        declines = [t for t in trends if t.direction == TrendDirection.DOWN]
        return {
            "metrics_tracked": len(trends),
            "improving": len(improvements),
            "declining": len(declines),
            "stable": len(trends) - len(improvements) - len(declines),
            "top_performers": [
                {"metric": t.metric_name, "change_pct": t.change_pct}
                for t in sorted(trends, key=lambda x: x.change_pct, reverse=True)[:5]
            ],
            "top_decliners": [
                {"metric": t.metric_name, "change_pct": t.change_pct}
                for t in sorted(trends, key=lambda x: x.change_pct)[:5]
            ],
        }

    def get_data_count(self) -> int:
        return len(self._data)
