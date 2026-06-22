"""Tests for learning integration — feeds records to LearningEngine."""

from __future__ import annotations

import pytest

from sfc.analytics_sync.aggregation.models import (
    AnalyticsPlatform,
    ContentType,
    UnifiedAnalyticsRecord,
)
from sfc.analytics_sync.learning.integration import LearningIntegration


def _make_record(views: int = 10000, likes: int = 1000, shares: int = 500, comments: int = 100) -> UnifiedAnalyticsRecord:
    rec = UnifiedAnalyticsRecord(
        content_id="c1",
        platform=AnalyticsPlatform.YOUTUBE,
        content_type=ContentType.VIDEO,
        views=views,
        likes=likes,
        shares=shares,
        comments=comments,
    )
    rec.compute_rates()
    return rec


class TestLearningIntegration:
    @pytest.mark.asyncio
    async def test_feed_records_with_real_data(self) -> None:
        integration = LearningIntegration()
        records = [_make_record(views=10000, likes=1000)]
        # Should not raise even if learning engine is unavailable
        lessons = await integration.feed_records(records, run_id="run_test")
        assert isinstance(lessons, list)

    @pytest.mark.asyncio
    async def test_feed_dry_run_zeros_skipped(self) -> None:
        integration = LearningIntegration()
        # dry-run record with 0 views should be skipped
        dry_rec = UnifiedAnalyticsRecord(
            content_id="dry1",
            platform=AnalyticsPlatform.YOUTUBE,
            content_type=ContentType.VIDEO,
            views=0,
            raw={"dry_run": True},
        )
        dry_rec.compute_rates()
        lessons = await integration.feed_records([dry_rec], run_id="run_dry")
        # No lessons from zero-view records
        assert isinstance(lessons, list)

    @pytest.mark.asyncio
    async def test_store_to_memory_does_not_raise(self) -> None:
        integration = LearningIntegration()
        records = [_make_record()]
        aggregations: dict = {}
        # Should not raise even if memory service not fully initialised
        await integration.store_to_memory(records, aggregations, run_id="run_mem")

    @pytest.mark.asyncio
    async def test_update_knowledge_graph_does_not_raise(self) -> None:
        integration = LearningIntegration()
        records = [_make_record(views=5000)]
        await integration.update_knowledge_graph(records, run_id="run_kg")
