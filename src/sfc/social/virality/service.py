"""Virality Prediction Engine — forecasts content virality across platforms."""

from __future__ import annotations

import logging
from typing import Any

from sfc.social.virality.models import (
    ContentFormat,
    ViralityBatch,
    ViralityForecast,
    ViralityMetrics,
    ViralityTier,
)

logger = logging.getLogger("sfc.social.virality")

_singleton: "ViralityPredictionEngine | None" = None

_ENGAGEMENT_RATE_BY_FORMAT: dict[str, float] = {
    ContentFormat.SHORT_VIDEO.value: 0.062,
    ContentFormat.LIVE.value: 0.071,
    ContentFormat.CAROUSEL.value: 0.048,
    ContentFormat.IMAGE.value: 0.038,
    ContentFormat.TEXT.value: 0.022,
    ContentFormat.LONG_VIDEO.value: 0.031,
    ContentFormat.STORY.value: 0.041,
    ContentFormat.THREAD.value: 0.028,
}

_SHARES_RATE_BY_FORMAT: dict[str, float] = {
    ContentFormat.SHORT_VIDEO.value: 0.014,
    ContentFormat.LIVE.value: 0.011,
    ContentFormat.CAROUSEL.value: 0.009,
    ContentFormat.IMAGE.value: 0.007,
    ContentFormat.TEXT.value: 0.006,
    ContentFormat.LONG_VIDEO.value: 0.008,
    ContentFormat.STORY.value: 0.005,
    ContentFormat.THREAD.value: 0.009,
}

_WATCH_TIME_BY_FORMAT: dict[str, float] = {
    ContentFormat.SHORT_VIDEO.value: 22.0,
    ContentFormat.LONG_VIDEO.value: 148.0,
    ContentFormat.LIVE.value: 320.0,
    ContentFormat.IMAGE.value: 8.0,
    ContentFormat.TEXT.value: 12.0,
    ContentFormat.CAROUSEL.value: 18.0,
    ContentFormat.STORY.value: 9.0,
    ContentFormat.THREAD.value: 35.0,
}


def get_virality_engine() -> "ViralityPredictionEngine":
    global _singleton
    if _singleton is None:
        _singleton = ViralityPredictionEngine()
    return _singleton


class ViralityPredictionEngine:
    """Predicts virality potential for Saudi football content."""

    def __init__(self) -> None:
        self._gateway = None
        self._forecasts: list[ViralityForecast] = []
        self._max_history = 2000

    @property
    def gateway(self):
        if self._gateway is None:
            from sfc.ai.model_gateway import get_ai_gateway
            self._gateway = get_ai_gateway()
        return self._gateway

    async def forecast(
        self,
        topic: str,
        content_type: str = "news",
        content_format: ContentFormat = ContentFormat.SHORT_VIDEO,
        platform: str = "x",
        trend_score: float = 50.0,
        sentiment_score: float = 0.0,
    ) -> ViralityForecast:
        """Generate a virality forecast for a specific content item."""
        virality_score = self._compute_virality_score(
            trend_score, sentiment_score, content_format
        )
        expected_reach = self._estimate_reach(virality_score, platform)
        probability = min(virality_score / 100, 0.98)

        fmt_val = content_format.value if hasattr(content_format, "value") else str(content_format)
        engagement_rate = _ENGAGEMENT_RATE_BY_FORMAT.get(fmt_val, 0.035)
        shares_rate = _SHARES_RATE_BY_FORMAT.get(fmt_val, 0.008)
        watch_time = _WATCH_TIME_BY_FORMAT.get(fmt_val, 20.0)
        follower_growth_rate = 0.002

        metrics = ViralityMetrics(
            virality_score=round(virality_score, 1),
            probability=round(probability, 2),
            expected_reach=expected_reach,
            expected_engagement=round(expected_reach * engagement_rate, 0),
            expected_shares=int(expected_reach * shares_rate),
            expected_views=int(expected_reach * 2.1),
            expected_watch_time_seconds=watch_time,
            expected_follower_growth=int(expected_reach * follower_growth_rate),
        )

        optimal_time = self._get_optimal_post_time(platform)
        hashtags = self._get_optimal_hashtags(topic, platform)
        recommendations = await self._get_recommendations(topic, metrics, content_format)

        forecast = ViralityForecast(
            content_type=content_type,
            content_format=content_format,
            platform=platform,
            topic=topic,
            metrics=metrics,
            optimal_post_time=optimal_time,
            optimal_hashtags=hashtags,
            recommendations=recommendations,
            optimization_tips=self._get_optimization_tips(content_format, platform),
        )

        if len(self._forecasts) < self._max_history:
            self._forecasts.append(forecast)

        return forecast

    async def forecast_batch(
        self,
        topics: list[str],
        platform: str = "x",
        content_format: ContentFormat = ContentFormat.SHORT_VIDEO,
    ) -> ViralityBatch:
        """Generate forecasts for multiple topics."""
        forecasts = []
        for topic in topics[:10]:
            f = await self.forecast(
                topic=topic,
                platform=platform,
                content_format=content_format,
            )
            forecasts.append(f)

        top = max(forecasts, key=lambda f: f.metrics.virality_score, default=None)
        avg_score = (
            sum(f.metrics.virality_score for f in forecasts) / len(forecasts)
            if forecasts else 0.0
        )
        total_reach = sum(f.metrics.expected_reach for f in forecasts)

        return ViralityBatch(
            forecasts=forecasts,
            top_forecast=top,
            avg_virality_score=round(avg_score, 1),
            total_expected_reach=total_reach,
        )

    async def get_recommendations(
        self,
        topic: str,
        platform: str = "x",
    ) -> list[str]:
        """Return actionable content recommendations for maximum virality."""
        forecast = await self.forecast(topic=topic, platform=platform)
        return forecast.recommendations + forecast.optimization_tips

    def get_history(self, limit: int = 50) -> list[dict[str, Any]]:
        return [f.to_dict() for f in self._forecasts[-limit:]]

    def _compute_virality_score(
        self,
        trend_score: float,
        sentiment_score: float,
        content_format: ContentFormat,
    ) -> float:
        format_boost = {
            ContentFormat.SHORT_VIDEO: 1.3,
            ContentFormat.LIVE: 1.25,
            ContentFormat.CAROUSEL: 1.1,
            ContentFormat.IMAGE: 1.05,
            ContentFormat.TEXT: 0.9,
            ContentFormat.LONG_VIDEO: 0.85,
            ContentFormat.STORY: 1.0,
            ContentFormat.THREAD: 0.95,
        }.get(content_format, 1.0)

        sentiment_boost = 1.0 + abs(sentiment_score) * 0.3
        # Deterministic base: 20 pts fixed floor + trend contribution
        base = trend_score * 0.6 + 20.0
        return min(base * format_boost * sentiment_boost, 100.0)

    def _estimate_reach(self, virality_score: float, platform: str) -> int:
        platform_multipliers = {
            "tiktok": 3.5,
            "instagram": 2.0,
            "x": 1.5,
            "youtube": 1.8,
            "reddit": 0.8,
        }
        multiplier = platform_multipliers.get(platform.lower(), 1.0)
        base_reach = int(virality_score ** 2 * 500)
        # Use fixed 1.0 multiplier (centre of original range 0.7-1.4)
        return int(base_reach * multiplier * 1.05)

    def _get_optimal_post_time(self, platform: str) -> str:
        times = {
            "x": "20:00 UTC",
            "instagram": "19:00 UTC",
            "tiktok": "21:00 UTC",
            "youtube": "17:00 UTC",
            "reddit": "14:00 UTC",
        }
        return times.get(platform.lower(), "18:00 UTC")

    def _get_optimal_hashtags(self, topic: str, platform: str) -> list[str]:
        base = [f"#{topic.replace(' ', '')}", "#SaudiFootball", "#SPL"]
        if platform == "tiktok":
            base.append("#FootballTikTok")
        elif platform == "instagram":
            base.append("#كرة_القدم_السعودية")
        return base

    async def _get_recommendations(
        self, topic: str, metrics: ViralityMetrics, content_format: ContentFormat
    ) -> list[str]:
        try:
            from sfc.ai.models import ModelRequest
            req = ModelRequest(
                prompt=f"Virality recommendations for {topic} on {content_format.value} (score={metrics.virality_score:.0f})",
                task_type="virality_prediction",
                max_tokens=200,
            )
            resp = await self.gateway.complete(req)
            return [resp.content]
        except Exception:
            tier = metrics.tier
            recs = [
                f"Post during peak hours for {tier.value} tier content",
                f"Use short-form {content_format.value} for maximum engagement",
            ]
            if tier in (ViralityTier.VIRAL, ViralityTier.HIGH):
                recs.append("Pin this content and boost with paid promotion")
            return recs

    def _get_optimization_tips(
        self, content_format: ContentFormat, platform: str
    ) -> list[str]:
        tips = ["Add Arabic subtitles for Saudi audience", "Include match highlights if available"]
        if content_format == ContentFormat.SHORT_VIDEO:
            tips.append("Keep under 60 seconds for maximum watch-through rate")
        if platform == "tiktok":
            tips.append("Use trending audio for 2x algorithmic boost")
        return tips
