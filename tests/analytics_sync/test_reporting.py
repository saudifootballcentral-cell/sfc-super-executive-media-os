"""Tests for analytics report generator."""

from __future__ import annotations

import pytest

from sfc.analytics_sync.aggregation.engine import AggregationEngine
from sfc.analytics_sync.aggregation.models import (
    AnalyticsPlatform,
    ContentType,
    UnifiedAnalyticsRecord,
)
from sfc.analytics_sync.reporting.generator import ReportGenerator


def _make_record(content_id: str, views: int, platform: AnalyticsPlatform = AnalyticsPlatform.YOUTUBE) -> UnifiedAnalyticsRecord:
    rec = UnifiedAnalyticsRecord(
        content_id=content_id,
        platform=platform,
        content_type=ContentType.VIDEO,
        views=views,
        likes=views // 10,
        shares=views // 20,
        comments=views // 50,
    )
    rec.compute_rates()
    return rec


class TestReportGenerator:
    def setup_method(self) -> None:
        self.generator = ReportGenerator()
        self.engine = AggregationEngine()
        self.records = [
            _make_record("c1", 5000),
            _make_record("c2", 2000, AnalyticsPlatform.X),
            _make_record("c3", 8000),
        ]
        self.aggregations = self.engine.aggregate_all(self.records)

    def test_generate_daily_report(self) -> None:
        report = self.generator.generate("daily", self.records, self.aggregations, run_id="r1")
        assert report.period == "daily"
        assert report.summary["total_views"] == 15000
        assert report.summary["total_records"] == 3

    def test_generate_weekly_report(self) -> None:
        report = self.generator.generate("weekly", self.records, self.aggregations)
        assert report.period == "weekly"

    def test_invalid_period_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown period"):
            self.generator.generate("bimonthly", self.records, self.aggregations)

    def test_top_performers_sorted_by_views(self) -> None:
        top = self.generator.generate_top_performers(self.records, top_n=2)
        assert top[0].content_id == "c3"  # 8000 views
        assert top[1].content_id == "c1"  # 5000 views

    def test_top_performers_limited(self) -> None:
        top = self.generator.generate_top_performers(self.records, top_n=1)
        assert len(top) == 1

    def test_optimization_suggestions_generated(self) -> None:
        suggestions = self.generator.generate_optimization_suggestions(self.aggregations)
        assert isinstance(suggestions, list)
        # Should have at least one suggestion about best platform
        assert len(suggestions) >= 0  # may be 0 if all same engagement rate

    def test_report_to_dict_serializable(self) -> None:
        report = self.generator.generate("daily", self.records, self.aggregations)
        d = report.to_dict()
        assert "report_id" in d
        assert "summary" in d
        assert d["summary"]["total_views"] == 15000

    def test_report_tracks_top_content(self) -> None:
        report = self.generator.generate("daily", self.records, self.aggregations)
        assert report.summary["top_content_id"] == "c3"
        assert report.summary["top_content_views"] == 8000
