"""Aggregation engine — rolls up UnifiedAnalyticsRecords across dimensions."""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime
from typing import Any

from sfc.analytics_sync.aggregation.models import AggregatedPerformance, UnifiedAnalyticsRecord

logger = logging.getLogger("sfc.analytics_sync.aggregation")


class AggregationEngine:
    """Aggregates analytics records by platform, persona, campaign, topic, and content type."""

    def aggregate_by_platform(
        self,
        records: list[UnifiedAnalyticsRecord],
        period: str = "daily",
    ) -> list[AggregatedPerformance]:
        return self._aggregate(records, dimension="platform", key_fn=lambda r: r.platform.value, period=period)

    def aggregate_by_persona(
        self,
        records: list[UnifiedAnalyticsRecord],
        period: str = "daily",
    ) -> list[AggregatedPerformance]:
        return self._aggregate(records, dimension="persona", key_fn=lambda r: r.persona_id or "unknown", period=period)

    def aggregate_by_campaign(
        self,
        records: list[UnifiedAnalyticsRecord],
        period: str = "daily",
    ) -> list[AggregatedPerformance]:
        return self._aggregate(records, dimension="campaign", key_fn=lambda r: r.campaign_id or "none", period=period)

    def aggregate_by_war_room(
        self,
        records: list[UnifiedAnalyticsRecord],
        period: str = "daily",
    ) -> list[AggregatedPerformance]:
        return self._aggregate(records, dimension="war_room", key_fn=lambda r: r.war_room_id or "none", period=period)

    def aggregate_by_topic(
        self,
        records: list[UnifiedAnalyticsRecord],
        period: str = "daily",
    ) -> list[AggregatedPerformance]:
        return self._aggregate(records, dimension="topic", key_fn=lambda r: r.topic or "unknown", period=period)

    def aggregate_by_content_type(
        self,
        records: list[UnifiedAnalyticsRecord],
        period: str = "daily",
    ) -> list[AggregatedPerformance]:
        return self._aggregate(records, dimension="content_type", key_fn=lambda r: r.content_type.value, period=period)

    def aggregate_all(
        self,
        records: list[UnifiedAnalyticsRecord],
        period: str = "daily",
    ) -> dict[str, list[AggregatedPerformance]]:
        """Run all aggregations and return as a dict keyed by dimension."""
        return {
            "platform": self.aggregate_by_platform(records, period),
            "persona": self.aggregate_by_persona(records, period),
            "campaign": self.aggregate_by_campaign(records, period),
            "topic": self.aggregate_by_topic(records, period),
            "content_type": self.aggregate_by_content_type(records, period),
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _aggregate(
        self,
        records: list[UnifiedAnalyticsRecord],
        dimension: str,
        key_fn: Any,
        period: str,
    ) -> list[AggregatedPerformance]:
        buckets: dict[str, list[UnifiedAnalyticsRecord]] = defaultdict(list)
        for r in records:
            buckets[key_fn(r)].append(r)

        results: list[AggregatedPerformance] = []
        for value, bucket in buckets.items():
            agg = self._build_agg(bucket, dimension, value, period)
            results.append(agg)
        return results

    def _build_agg(
        self,
        records: list[UnifiedAnalyticsRecord],
        dimension: str,
        value: str,
        period: str,
    ) -> AggregatedPerformance:
        total_views = sum(r.views for r in records)
        total_impressions = sum(r.impressions for r in records)
        total_reach = sum(r.reach for r in records)
        total_likes = sum(r.likes for r in records)
        total_shares = sum(r.shares for r in records)
        total_comments = sum(r.comments for r in records)
        total_watch = sum(r.watch_time_seconds for r in records)
        total_subs = sum(r.subscribers_gained for r in records)
        total_followers = sum(r.followers_gained for r in records)

        eng_rates = [r.engagement_rate for r in records if r.engagement_rate > 0]
        ret_rates = [r.retention_rate for r in records if r.retention_rate > 0]
        ctrs = [r.ctr for r in records if r.ctr > 0]
        avg_eng = sum(eng_rates) / len(eng_rates) if eng_rates else 0.0
        avg_ret = sum(ret_rates) / len(ret_rates) if ret_rates else 0.0
        avg_ctr = sum(ctrs) / len(ctrs) if ctrs else 0.0

        # Top content by views
        top = max(records, key=lambda r: r.views, default=None)

        return AggregatedPerformance(
            dimension=dimension,
            dimension_value=value,
            period=period,
            record_count=len(records),
            total_views=total_views,
            total_impressions=total_impressions,
            total_reach=total_reach,
            total_likes=total_likes,
            total_shares=total_shares,
            total_comments=total_comments,
            total_watch_time_seconds=total_watch,
            avg_engagement_rate=round(avg_eng, 4),
            avg_retention_rate=round(avg_ret, 4),
            avg_ctr=round(avg_ctr, 4),
            top_content_id=top.content_id if top else "",
            top_content_views=top.views if top else 0,
            subscribers_gained=total_subs,
            followers_gained=total_followers,
            records=[r.record_id for r in records],
        )


_singleton: AggregationEngine | None = None


def get_aggregation_engine() -> AggregationEngine:
    global _singleton
    if _singleton is None:
        _singleton = AggregationEngine()
    return _singleton
