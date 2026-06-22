"""Tests for AnalyticsStore JSON persistence."""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

import pytest

from sfc.analytics_sync.aggregation.models import (
    AggregatedPerformance,
    AnalyticsPlatform,
    ContentType,
    UnifiedAnalyticsRecord,
)
from sfc.analytics_sync.storage.store import AnalyticsStore


@pytest.fixture
def tmp_store(tmp_path: Path) -> AnalyticsStore:
    return AnalyticsStore(storage_root=tmp_path / "analytics")


def _make_record(content_id: str = "c1") -> UnifiedAnalyticsRecord:
    return UnifiedAnalyticsRecord(
        content_id=content_id,
        platform=AnalyticsPlatform.YOUTUBE,
        content_type=ContentType.VIDEO,
        views=5000,
        likes=500,
    )


class TestAnalyticsStore:
    @pytest.mark.asyncio
    async def test_save_and_retrieve_record(self, tmp_store: AnalyticsStore) -> None:
        rec = _make_record("vid1")
        rec_id = await tmp_store.save_record(rec)
        retrieved = await tmp_store.get_record(rec_id)
        assert retrieved is not None
        assert retrieved.content_id == "vid1"
        assert retrieved.views == 5000

    @pytest.mark.asyncio
    async def test_get_missing_record_returns_none(self, tmp_store: AnalyticsStore) -> None:
        result = await tmp_store.get_record("nonexistent-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_list_records(self, tmp_store: AnalyticsStore) -> None:
        for i in range(3):
            await tmp_store.save_record(_make_record(f"c{i}"))
        records = await tmp_store.list_records()
        assert len(records) == 3

    @pytest.mark.asyncio
    async def test_list_records_filter_by_platform(self, tmp_store: AnalyticsStore) -> None:
        await tmp_store.save_record(_make_record("yt1"))
        x_rec = UnifiedAnalyticsRecord(
            content_id="x1",
            platform=AnalyticsPlatform.X,
            content_type=ContentType.POST,
            views=100,
        )
        await tmp_store.save_record(x_rec)
        yt_records = await tmp_store.list_records(platform="youtube")
        assert all(r.platform == AnalyticsPlatform.YOUTUBE for r in yt_records)

    @pytest.mark.asyncio
    async def test_delete_record(self, tmp_store: AnalyticsStore) -> None:
        rec = _make_record("del1")
        rec_id = await tmp_store.save_record(rec)
        deleted = await tmp_store.delete_record(rec_id)
        assert deleted is True
        result = await tmp_store.get_record(rec_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_save_and_list_aggregated(self, tmp_store: AnalyticsStore) -> None:
        agg = AggregatedPerformance(
            dimension="platform",
            dimension_value="youtube",
            period="daily",
            total_views=10000,
        )
        agg_id = await tmp_store.save_aggregated(agg)
        results = await tmp_store.list_aggregated(dimension="platform")
        assert len(results) >= 1
        assert any(a.agg_id == agg_id for a in results)

    @pytest.mark.asyncio
    async def test_get_stats(self, tmp_store: AnalyticsStore) -> None:
        await tmp_store.save_record(_make_record())
        stats = await tmp_store.get_stats()
        assert stats["total_records"] == 1
        assert stats["backend"] == "json"
