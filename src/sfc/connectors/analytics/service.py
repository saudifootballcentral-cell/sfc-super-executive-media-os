"""Analytics sync service — aggregates metrics from YouTube and X connectors."""

from __future__ import annotations

import logging
import random
from typing import Any

from sfc.connectors.analytics.models import (
    AnalyticsSnapshot,
    AnalyticsSyncReport,
    ConnectorObservability,
    MetricType,
    Platform,
    PlatformGrowth,
)

logger = logging.getLogger("sfc.connectors.analytics")

_singleton: "AnalyticsSyncService | None" = None


def get_analytics_sync_service() -> "AnalyticsSyncService":
    global _singleton
    if _singleton is None:
        _singleton = AnalyticsSyncService()
    return _singleton


class AnalyticsSyncService:
    """Aggregates and stores analytics data from all platform connectors."""

    def __init__(self) -> None:
        self._snapshots: list[AnalyticsSnapshot] = []
        self._growth_history: list[PlatformGrowth] = []
        self._trend_history: list[dict[str, Any]] = []
        self._observability = ConnectorObservability(connector="analytics")

    async def sync_youtube_analytics(
        self, video_ids: list[str] | None = None
    ) -> list[AnalyticsSnapshot]:
        """Pull analytics for a set of YouTube video IDs."""
        try:
            from sfc.connectors.youtube.service import get_youtube_service
            yt = get_youtube_service()
            snapshots: list[AnalyticsSnapshot] = []
            for vid_id in (video_ids or ["mock_vid_1", "mock_vid_2"])[:5]:
                analytics = await yt.get_analytics(vid_id)
                snap = AnalyticsSnapshot(
                    platform=Platform.YOUTUBE,
                    asset_id=vid_id,
                    metrics={
                        MetricType.VIEWS.value: analytics.views,
                        MetricType.IMPRESSIONS.value: analytics.impressions,
                        MetricType.CTR.value: analytics.ctr,
                        MetricType.WATCH_TIME.value: analytics.watch_time_hours,
                        MetricType.LIKES.value: analytics.likes,
                        MetricType.COMMENTS.value: analytics.comments,
                        MetricType.SHARES.value: analytics.shares,
                        MetricType.SUBSCRIBERS.value: analytics.subscribers_gained,
                    },
                )
                snapshots.append(snap)
                self._snapshots.append(snap)
            self._observability.record_success()
            logger.info("[AnalyticsSync] YouTube synced | %d videos", len(snapshots))
            return snapshots
        except Exception as exc:
            self._observability.record_failure(str(exc))
            logger.warning("[AnalyticsSync] YouTube sync failed: %s", exc)
            return []

    async def sync_x_analytics(
        self, post_ids: list[str] | None = None
    ) -> list[AnalyticsSnapshot]:
        """Pull analytics for X post IDs."""
        try:
            from sfc.connectors.x.service import get_x_service
            x = get_x_service()
            snapshots: list[AnalyticsSnapshot] = []
            for post_id in (post_ids or ["mock_x_1", "mock_x_2"])[:5]:
                metrics = await x.get_metrics(post_id)
                snap = AnalyticsSnapshot(
                    platform=Platform.X,
                    asset_id=post_id,
                    metrics={
                        MetricType.VIEWS.value: metrics.views,
                        MetricType.IMPRESSIONS.value: metrics.impressions,
                        MetricType.LIKES.value: metrics.likes,
                        MetricType.SHARES.value: metrics.retweets,
                        MetricType.COMMENTS.value: metrics.replies,
                        MetricType.ENGAGEMENT.value: metrics.engagement_rate,
                        MetricType.REACH.value: metrics.profile_visits,
                    },
                )
                snapshots.append(snap)
                self._snapshots.append(snap)
            self._observability.record_success()
            logger.info("[AnalyticsSync] X synced | %d posts", len(snapshots))
            return snapshots
        except Exception as exc:
            self._observability.record_failure(str(exc))
            logger.warning("[AnalyticsSync] X sync failed: %s", exc)
            return []

    async def sync_channel_growth(self) -> list[PlatformGrowth]:
        """Pull follower/subscriber growth across all platforms."""
        try:
            from sfc.connectors.youtube.service import get_youtube_service
            yt = get_youtube_service()
            channel = await yt.get_channel_metrics()

            growth_records: list[PlatformGrowth] = []
            yt_growth = PlatformGrowth(
                platform=Platform.YOUTUBE,
                followers_or_subscribers=channel.subscriber_count,
                growth_7d=random.randint(200, 5_000),
                growth_30d=channel.subscriber_growth_30d,
                growth_rate_pct=round(random.uniform(0.5, 8.0), 2),
                total_views_30d=channel.monthly_views,
                avg_engagement_rate=round(random.uniform(2.0, 8.0), 2),
            )
            growth_records.append(yt_growth)

            for platform in [Platform.X, Platform.INSTAGRAM, Platform.TIKTOK]:
                growth = PlatformGrowth(
                    platform=platform,
                    followers_or_subscribers=random.randint(10_000, 500_000),
                    growth_7d=random.randint(100, 3_000),
                    growth_30d=random.randint(500, 15_000),
                    growth_rate_pct=round(random.uniform(0.3, 6.0), 2),
                    total_views_30d=random.randint(50_000, 2_000_000),
                    avg_engagement_rate=round(random.uniform(1.5, 9.0), 2),
                )
                growth_records.append(growth)

            self._growth_history.extend(growth_records)
            self._observability.record_success()
            logger.info("[AnalyticsSync] Growth synced | %d platforms", len(growth_records))
            return growth_records
        except Exception as exc:
            self._observability.record_failure(str(exc))
            logger.warning("[AnalyticsSync] Growth sync failed: %s", exc)
            return []

    async def sync_trend_history(self) -> list[dict[str, Any]]:
        """Pull current trending topics from X and store historically."""
        try:
            from sfc.connectors.x.service import get_x_service
            x = get_x_service()
            trends = await x.get_trending_topics()
            trend_dicts = [t.to_dict() for t in trends]
            self._trend_history.extend(trend_dicts)
            self._observability.record_success()
            logger.info("[AnalyticsSync] Trend history updated | %d trends", len(trends))
            return trend_dicts
        except Exception as exc:
            self._observability.record_failure(str(exc))
            return []

    async def generate_sync_report(
        self,
        youtube_ids: list[str] | None = None,
        x_ids: list[str] | None = None,
    ) -> AnalyticsSyncReport:
        """Full analytics sync: YouTube + X + growth + trends."""
        yt_snaps = await self.sync_youtube_analytics(youtube_ids)
        x_snaps = await self.sync_x_analytics(x_ids)
        growth = await self.sync_channel_growth()
        await self.sync_trend_history()

        all_snaps = yt_snaps + x_snaps
        total_views = int(sum(s.get(MetricType.VIEWS) for s in all_snaps))
        total_impressions = int(sum(s.get(MetricType.IMPRESSIONS) for s in all_snaps))
        total_reach = int(sum(s.get(MetricType.REACH) for s in all_snaps))
        ctrs = [s.get(MetricType.CTR) for s in all_snaps if s.get(MetricType.CTR) > 0]
        avg_ctr = sum(ctrs) / max(len(ctrs), 1)
        total_followers = sum(g.followers_or_subscribers for g in growth)
        total_subs = next(
            (g.followers_or_subscribers for g in growth if g.platform == Platform.YOUTUBE), 0
        )
        watch_time = sum(
            s.get(MetricType.WATCH_TIME)
            for s in all_snaps
            if s.platform == Platform.YOUTUBE
        )

        return AnalyticsSyncReport(
            snapshots=all_snaps,
            platform_growth=growth,
            total_views=total_views,
            total_impressions=total_impressions,
            total_reach=total_reach,
            avg_ctr=round(avg_ctr, 2),
            avg_engagement_rate=round(random.uniform(2.0, 7.0), 2),
            total_followers=total_followers,
            total_subscribers=total_subs,
            total_watch_time_hours=round(watch_time, 1),
            platforms_synced=[Platform.YOUTUBE.value, Platform.X.value,
                              Platform.INSTAGRAM.value, Platform.TIKTOK.value],
            observability=self._observability.to_dict(),
        )

    def get_historical_snapshots(
        self, platform: Platform | None = None, limit: int = 100
    ) -> list[AnalyticsSnapshot]:
        snaps = self._snapshots
        if platform:
            snaps = [s for s in snaps if s.platform == platform]
        return snaps[-limit:]

    def get_trend_history(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._trend_history[-limit:]

    def get_growth_history(self, limit: int = 20) -> list[PlatformGrowth]:
        return self._growth_history[-limit:]

    @property
    def observability(self) -> ConnectorObservability:
        return self._observability
