"""Tests for aggregation engine and UnifiedAnalyticsRecord."""

from __future__ import annotations

import pytest

from sfc.analytics_sync.aggregation.engine import AggregationEngine
from sfc.analytics_sync.aggregation.models import (
    AnalyticsPlatform,
    ContentType,
    UnifiedAnalyticsRecord,
)


def _make_record(
    content_id: str = "c1",
    platform: AnalyticsPlatform = AnalyticsPlatform.YOUTUBE,
    views: int = 1000,
    likes: int = 100,
    shares: int = 50,
    comments: int = 20,
    persona_id: str = "p1",
    topic: str = "goal",
) -> UnifiedAnalyticsRecord:
    rec = UnifiedAnalyticsRecord(
        content_id=content_id,
        platform=platform,
        content_type=ContentType.VIDEO,
        views=views,
        likes=likes,
        shares=shares,
        comments=comments,
        persona_id=persona_id,
        topic=topic,
    )
    rec.compute_rates()
    return rec


class TestUnifiedAnalyticsRecord:
    def test_compute_rates_calculates_engagement(self) -> None:
        rec = _make_record(views=1000, likes=100, shares=50, comments=20)
        assert rec.engagement_rate == pytest.approx((170 / 1000) * 100, abs=0.01)

    def test_compute_rates_zero_views_no_division_error(self) -> None:
        rec = _make_record(views=0, likes=0, shares=0, comments=0)
        # Should not raise; 0/max(0,1) = 0
        assert rec.engagement_rate == 0.0

    def test_to_dict_serializable(self) -> None:
        rec = _make_record()
        d = rec.to_dict()
        assert isinstance(d, dict)
        assert "record_id" in d
        assert "platform" in d


class TestAggregationEngine:
    def setup_method(self) -> None:
        self.engine = AggregationEngine()
        self.records = [
            _make_record("c1", AnalyticsPlatform.YOUTUBE, views=5000, likes=500, persona_id="p1", topic="goal"),
            _make_record("c2", AnalyticsPlatform.X, views=2000, likes=200, persona_id="p1", topic="penalty"),
            _make_record("c3", AnalyticsPlatform.YOUTUBE, views=3000, likes=300, persona_id="p2", topic="goal"),
            _make_record("c4", AnalyticsPlatform.BUFFER, views=1000, likes=100, persona_id="p2", topic="save"),
        ]

    def test_aggregate_by_platform(self) -> None:
        aggs = self.engine.aggregate_by_platform(self.records)
        platforms = {a.dimension_value for a in aggs}
        assert "youtube" in platforms
        assert "x" in platforms
        assert "buffer" in platforms

    def test_platform_total_views_correct(self) -> None:
        aggs = self.engine.aggregate_by_platform(self.records)
        yt_agg = next(a for a in aggs if a.dimension_value == "youtube")
        assert yt_agg.total_views == 8000

    def test_aggregate_by_persona(self) -> None:
        aggs = self.engine.aggregate_by_persona(self.records)
        personas = {a.dimension_value for a in aggs}
        assert "p1" in personas
        assert "p2" in personas

    def test_aggregate_by_topic(self) -> None:
        aggs = self.engine.aggregate_by_topic(self.records)
        topics = {a.dimension_value for a in aggs}
        assert "goal" in topics

    def test_goal_topic_record_count(self) -> None:
        aggs = self.engine.aggregate_by_topic(self.records)
        goal_agg = next(a for a in aggs if a.dimension_value == "goal")
        assert goal_agg.record_count == 2

    def test_aggregate_all_returns_all_dimensions(self) -> None:
        all_aggs = self.engine.aggregate_all(self.records)
        assert "platform" in all_aggs
        assert "persona" in all_aggs
        assert "topic" in all_aggs
        assert "content_type" in all_aggs

    def test_top_content_tracked(self) -> None:
        aggs = self.engine.aggregate_by_platform(self.records)
        yt_agg = next(a for a in aggs if a.dimension_value == "youtube")
        assert yt_agg.top_content_id == "c1"
        assert yt_agg.top_content_views == 5000

    def test_empty_records_returns_empty(self) -> None:
        aggs = self.engine.aggregate_by_platform([])
        assert aggs == []
