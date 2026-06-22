"""AnalyticsSyncLayerService — orchestrates all analytics sync providers."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sfc.analytics_sync.aggregation.engine import AggregationEngine, get_aggregation_engine
from sfc.analytics_sync.aggregation.models import UnifiedAnalyticsRecord
from sfc.analytics_sync.learning.integration import LearningIntegration, get_learning_integration
from sfc.analytics_sync.providers.buffer import BufferAnalyticsProvider, get_buffer_analytics_provider
from sfc.analytics_sync.providers.x import XAnalyticsProvider, get_x_analytics_provider
from sfc.analytics_sync.providers.youtube import YouTubeAnalyticsProvider, get_youtube_analytics_provider
from sfc.analytics_sync.reporting.generator import AnalyticsReport, ReportGenerator, get_report_generator
from sfc.analytics_sync.storage.store import AnalyticsStore, get_analytics_store

logger = logging.getLogger("sfc.analytics_sync")


class AnalyticsSyncLayerService:
    """Top-level service for Package 9C — Analytics Sync Layer.

    Fetches metrics from YouTube, X, and Buffer; normalises them into
    UnifiedAnalyticsRecords; aggregates; feeds the learning engine;
    stores to disk; and fires audit events on the event bus.
    """

    def __init__(
        self,
        youtube_provider: YouTubeAnalyticsProvider | None = None,
        x_provider: XAnalyticsProvider | None = None,
        buffer_provider: BufferAnalyticsProvider | None = None,
        aggregation_engine: AggregationEngine | None = None,
        learning: LearningIntegration | None = None,
        report_generator: ReportGenerator | None = None,
        store: AnalyticsStore | None = None,
    ) -> None:
        self._youtube = youtube_provider or get_youtube_analytics_provider()
        self._x = x_provider or get_x_analytics_provider()
        self._buffer = buffer_provider or get_buffer_analytics_provider()
        self._agg = aggregation_engine or get_aggregation_engine()
        self._learning = learning or get_learning_integration()
        self._reporter = report_generator or get_report_generator()
        self._store = store or get_analytics_store()

    # ------------------------------------------------------------------
    # Main entry points
    # ------------------------------------------------------------------

    async def sync(
        self,
        run_id: str,
        *,
        youtube_video_ids: list[str] | None = None,
        x_tweet_ids: list[str] | None = None,
        buffer_posts: list[dict[str, str]] | None = None,
        period: str = "daily",
        feed_learning: bool = True,
    ) -> dict[str, Any]:
        """Full sync cycle: fetch → normalise → aggregate → learn → store → report.

        Args:
            run_id: Workflow run identifier.
            youtube_video_ids: List of YouTube video IDs to fetch metrics for.
            x_tweet_ids: List of X tweet IDs to fetch metrics for.
            buffer_posts: List of {"profile_id": ..., "post_id": ...} dicts.
            period: Aggregation period — hourly/daily/weekly/monthly/quarterly.
            feed_learning: Whether to send records to LearningEngine.

        Returns:
            Summary dict with record count, lessons count, and report.
        """
        records: list[UnifiedAnalyticsRecord] = []

        # --- YouTube ---
        for vid_id in (youtube_video_ids or []):
            rec = await self._youtube.fetch_video_metrics(vid_id, run_id=run_id)
            records.append(rec)

        # Channel-level
        ch_rec = await self._youtube.fetch_channel_metrics(run_id=run_id)
        if ch_rec.views > 0 or ch_rec.raw.get("dry_run"):
            records.append(ch_rec)

        # --- X ---
        for tweet_id in (x_tweet_ids or []):
            rec = await self._x.fetch_tweet_metrics(tweet_id, run_id=run_id)
            records.append(rec)

        # --- Buffer ---
        for bp in (buffer_posts or []):
            rec = await self._buffer.fetch_post_metrics(
                bp.get("profile_id", ""),
                bp.get("post_id", ""),
                run_id=run_id,
            )
            records.append(rec)

        # --- Aggregate ---
        aggregations = self._agg.aggregate_all(records, period=period)

        # --- Persist ---
        for rec in records:
            await self._store.save_record(rec)
        for aggs in aggregations.values():
            for agg in aggs:
                await self._store.save_aggregated(agg)

        # --- Generate report ---
        report = self._reporter.generate(period, records, aggregations, run_id=run_id)

        # --- Learning ---
        lessons: list[Any] = []
        if feed_learning:
            lessons = await self._learning.feed_records(records, run_id=run_id)
            await self._learning.store_to_memory(records, aggregations, run_id=run_id)
            await self._learning.update_knowledge_graph(records, run_id=run_id)

        # --- Events ---
        self._fire_events(run_id, records, report, lessons)

        top_performers = self._reporter.generate_top_performers(records, top_n=5)
        optimizations = self._reporter.generate_optimization_suggestions(aggregations)

        logger.info(
            "[AnalyticsSync] run=%s period=%s records=%d lessons=%d",
            run_id, period, len(records), len(lessons),
        )
        return {
            "run_id": run_id,
            "period": period,
            "record_count": len(records),
            "lesson_count": len(lessons),
            "report": report.to_dict(),
            "top_performers": [r.to_dict() for r in top_performers],
            "optimizations": optimizations,
        }

    async def sync_for_content(
        self,
        content_id: str,
        run_id: str,
        platform: str = "youtube",
        period: str = "daily",
    ) -> UnifiedAnalyticsRecord:
        """Sync analytics for a single content piece across one platform."""
        if platform == "youtube":
            rec = await self._youtube.fetch_video_metrics(content_id, run_id=run_id)
        elif platform in ("x", "twitter"):
            rec = await self._x.fetch_tweet_metrics(content_id, run_id=run_id)
        else:
            rec = await self._buffer.fetch_post_metrics("", content_id, run_id=run_id)
        await self._store.save_record(rec)
        return rec

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _fire_events(
        self,
        run_id: str,
        records: list[UnifiedAnalyticsRecord],
        report: AnalyticsReport,
        lessons: list[Any],
    ) -> None:
        try:
            from sfc.events.bus import get_event_bus
            from sfc.events.types import (
                AnalyticsRetrieved,
                LearningGenerated,
                TopPerformerDetected,
            )
            bus = get_event_bus()
            bus.publish(AnalyticsRetrieved(
                division="analytics",
                run_id=run_id,
                payload={"record_count": len(records), "period": report.period},
            ))
            if lessons:
                bus.publish(LearningGenerated(
                    division="analytics",
                    run_id=run_id,
                    payload={"lesson_count": len(lessons)},
                ))
            top = max(records, key=lambda r: r.views, default=None)
            if top and top.views > 0:
                bus.publish(TopPerformerDetected(
                    division="analytics",
                    run_id=run_id,
                    payload={"content_id": top.content_id, "views": top.views, "platform": top.platform.value},
                ))
        except Exception as exc:
            logger.warning("[AnalyticsSync] Event firing failed: %s", exc)


_singleton: AnalyticsSyncLayerService | None = None


def get_analytics_sync_service() -> AnalyticsSyncLayerService:
    global _singleton
    if _singleton is None:
        _singleton = AnalyticsSyncLayerService()
    return _singleton
