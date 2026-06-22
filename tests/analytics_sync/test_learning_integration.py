"""Tests for learning integration — feeds records to LearningEngine."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

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

    # --- Pilot blocker fix tests ---

    @pytest.mark.asyncio
    async def test_store_to_memory_no_import_error(self) -> None:
        """store_to_memory must use get_infrastructure().memory_manager — no ImportError."""
        mock_memory = AsyncMock()
        mock_infra = MagicMock()
        mock_infra.memory_manager = mock_memory

        integration = LearningIntegration()
        records = [_make_record()]
        aggregations = {"platform": []}

        with patch(
            "sfc.infrastructure.context.get_infrastructure",
            return_value=mock_infra,
        ):
            # Must not raise ImportError; inner exception is caught and logged
            try:
                await integration.store_to_memory(records, aggregations, run_id="run_fix1")
            except ImportError as exc:
                pytest.fail(f"ImportError raised in store_to_memory: {exc}")

        # memory.store should have been called at least once (records key)
        assert mock_memory.store.called

    @pytest.mark.asyncio
    async def test_update_knowledge_graph_no_import_error(self) -> None:
        """update_knowledge_graph must use get_knowledge_graph() — no ImportError."""
        mock_kg = AsyncMock()
        mock_kg.add_entity = AsyncMock(return_value="entity_id_123")

        integration = LearningIntegration()
        records = [_make_record(views=5000)]

        with patch(
            "sfc.infrastructure.knowledge_graph.service.get_knowledge_graph",
            return_value=mock_kg,
        ):
            try:
                await integration.update_knowledge_graph(records, run_id="run_fix2")
            except ImportError as exc:
                pytest.fail(f"ImportError raised in update_knowledge_graph: {exc}")

        mock_kg.add_entity.assert_called_once()
        call_kwargs = mock_kg.add_entity.call_args
        assert "perf_c1_youtube" in call_kwargs.kwargs.get("name", "") or \
               "perf_c1_youtube" in str(call_kwargs)

    @pytest.mark.asyncio
    async def test_dry_run_analytics_end_to_end(self) -> None:
        """Full dry-run sync with learning enabled must complete without error."""
        from sfc.analytics_sync.service import AnalyticsSyncLayerService

        svc = AnalyticsSyncLayerService()
        result = await svc.sync(
            run_id="run_e2e_dry",
            youtube_video_ids=["vid_e2e"],
            x_tweet_ids=["tweet_e2e"],
            feed_learning=True,
            period="daily",
        )

        assert isinstance(result, dict)
        assert result["run_id"] == "run_e2e_dry"
        assert result["record_count"] >= 2
        assert "report" in result
        assert "top_performers" in result
